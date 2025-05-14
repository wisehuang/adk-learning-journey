"""Manager agent implementation for the project management system.

The Manager agent is responsible for:
1. Task assignment based on workload and priority
2. Project oversight and coordination
3. Status reporting
4. Decision making for task approval or rejection
"""

import json
import uuid
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import FunctionTool
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel as PydanticBaseModel, ConfigDict

from ...common import Task, TaskStatus, TaskPriority, TaskType, AgentLoad


# FastAPI models for request/response
class CreateTaskRequest(PydanticBaseModel):
    """Request model for creating a task."""
    title: str
    description: str
    priority: Optional[str] = "medium"
    task_type: str

class CreateTaskResponse(PydanticBaseModel):
    """Response model for creating a task."""
    task_id: str
    status: str

class AssignTaskRequest(PydanticBaseModel):
    """Request model for assigning a task."""
    task_id: str
    agent_id: Optional[str] = None

class AssignTaskResponse(PydanticBaseModel):
    """Response model for assigning a task."""
    status: str
    assigned_to: Optional[str] = None

class ListTasksRequest(PydanticBaseModel):
    """Request model for listing tasks."""
    status: Optional[str] = None

class TaskInfo(PydanticBaseModel):
    """Basic task information."""
    id: str
    title: str
    status: str
    priority: str
    assigned_to: Optional[str] = None

class ListTasksResponse(PydanticBaseModel):
    """Response model for listing tasks."""
    tasks: List[TaskInfo]

class ReviewTaskRequest(PydanticBaseModel):
    """Request model for reviewing a task."""
    task_id: str
    approve: bool
    comment: Optional[str] = None

class ReviewTaskResponse(PydanticBaseModel):
    """Response model for reviewing a task."""
    status: str
    new_task_status: str

class AgentStatusResponse(PydanticBaseModel):
    """Response model for agent status."""
    agent_id: str
    agent_type: str
    current_tasks: int
    max_capacity: int
    load_percentage: float

class GetAgentStatusResponse(PydanticBaseModel):
    """Response model for getting agent status."""
    agents: List[AgentStatusResponse]


class ManagerAgent(BaseAgent):
    """Manager agent for the project management system."""
    
    # Add model_config to allow arbitrary attributes when Pydantic v2 is used
    model_config = ConfigDict(extra="allow")
    
    # OR uncomment these for Pydantic v1 if ConfigDict doesn't work
    # class Config:
    #     extra = "allow"
    
    def __init__(self, name: str, tasks_store: Dict[str, Task], agent_loads: Dict[str, AgentLoad]):
        """Initialize the Manager agent.
        
        Args:
            name: The name of the agent.
            tasks_store: Reference to the shared tasks store.
            agent_loads: Reference to the agent load information.
        """
        super().__init__(name=name)
        self.tasks_store = tasks_store
        self.agent_loads = agent_loads
        
        # Create API app
        self.app = FastAPI(title="Project Manager Agent API")
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up the API routes for the manager agent."""
        # Load agent manifest
        manifest_path = os.path.join(os.path.dirname(__file__), ".well-known", "agent.json")
        try:
            with open(manifest_path, "r") as f:
                self.manifest = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load agent manifest: {e}")
            self.manifest = {}
        
        # Set up routes based on capabilities
        self.app.post("/api/agents/manager/create_task")(self.api_create_task)
        self.app.post("/api/agents/manager/assign_task")(self.api_assign_task)
        self.app.post("/api/agents/manager/list_tasks")(self.api_list_tasks)
        self.app.post("/api/agents/manager/review_task")(self.api_review_task)
        self.app.post("/api/agents/manager/get_agent_status")(self.api_get_agent_status)
        
    async def _run_async_impl(self, ctx: InvocationContext):
        """Run the Manager agent's async implementation.
        
        This is the main entry point for the Manager agent.
        
        Args:
            ctx: The invocation context.
            
        Yields:
            Events to communicate with other agents and the system.
        """
        # Get input message
        input_message = ctx.session.get_latest_message()
        
        if not input_message:
            yield Event(
                author=self.name,
                content="No input message provided. Please provide a command.",
            )
            return
            
        user_input = input_message.content
        
        # Process user command using A2A protocol
        if "create task" in user_input.lower():
            # Extract task details from user input
            parts = user_input.split('"')
            title = parts[1] if len(parts) > 1 else f"Task {str(uuid.uuid4())[:8]}"
            description = parts[3] if len(parts) > 3 else "No description provided"
            
            # Determine priority and task type
            priority = TaskPriority.MEDIUM.value
            for p in TaskPriority:
                if p.value in user_input.lower():
                    priority = p.value
                    break
                    
            task_type = TaskType.FEATURE.value
            for t in TaskType:
                if t.value in user_input.lower():
                    task_type = t.value
                    break
            
            # Create request object
            request = CreateTaskRequest(
                title=title,
                description=description,
                priority=priority,
                task_type=task_type
            )
            
            # Call API method
            response = await self.api_create_task(request)
            
            yield Event(
                author=self.name,
                content=f"Task created: {response.task_id} - {title}"
            )
            
        elif "assign task" in user_input.lower():
            # Extract task ID from input
            parts = user_input.lower().split()
            task_id = None
            agent_id = None
            
            for part in parts:
                if part.startswith("task-"):
                    task_id = part.upper()
                    break
            
            # Check if specific agent mentioned
            for agent_id_check in self.agent_loads:
                if agent_id_check.lower() in user_input.lower():
                    agent_id = agent_id_check
                    break
            
            if not task_id:
                yield Event(
                    author=self.name,
                    content="Please specify a task ID to assign (e.g., TASK-12345678)"
                )
                return
            
            # Create request
            request = AssignTaskRequest(task_id=task_id, agent_id=agent_id)
            
            # Call API method
            response = await self.api_assign_task(request)
            
            yield Event(
                author=self.name,
                content=response.status
            )
            
        elif "list tasks" in user_input.lower():
            # Extract status filter if any
            status_filter = None
            for status in TaskStatus:
                if status.value in user_input.lower():
                    status_filter = status.value
                    break
            
            # Create request
            request = ListTasksRequest(status=status_filter)
            
            # Call API method
            response = await self.api_list_tasks(request)
            
            # Format the response
            if not response.tasks:
                result = "No tasks available."
            else:
                result = "Tasks:\n"
                for task in response.tasks:
                    result += (
                        f"- {task.id}: {task.title} [{task.status}] "
                        f"Priority: {task.priority} | Assigned to: {task.assigned_to or 'Unassigned'}\n"
                    )
            
            yield Event(
                author=self.name,
                content=result
            )
            
        elif "review task" in user_input.lower():
            # Extract task ID and approval decision
            parts = user_input.lower().split()
            task_id = None
            for part in parts:
                if part.startswith("task-"):
                    task_id = part.upper()
                    break
            
            if not task_id:
                yield Event(
                    author=self.name,
                    content="Please specify a task ID to review (e.g., TASK-12345678)"
                )
                return
            
            # Determine approval
            approve = True
            for part in parts:
                if part in ["reject", "rejected", "fail", "failed"]:
                    approve = False
                    break
            
            # Create request
            request = ReviewTaskRequest(task_id=task_id, approve=approve)
            
            # Call API method
            response = await self.api_review_task(request)
            
            yield Event(
                author=self.name,
                content=response.status
            )
            
        elif "agent status" in user_input.lower():
            # Call API method
            response = await self.api_get_agent_status({})
            
            # Format the response
            result = "Agent Status Report:\n"
            for agent in response.agents:
                result += (
                    f"- {agent.agent_id} ({agent.agent_type}): "
                    f"{agent.current_tasks}/{agent.max_capacity} tasks "
                    f"({agent.load_percentage:.1f}% load)\n"
                )
            
            yield Event(
                author=self.name,
                content=result
            )
            
        else:
            yield Event(
                author=self.name,
                content=(
                    "I'm the project manager. I can help with: "
                    "create task, assign task, list tasks, review task, agent status"
                )
            )

    # API implementations matching the agent.json capabilities
    async def api_create_task(self, request: CreateTaskRequest = Body(...)) -> CreateTaskResponse:
        """API endpoint to create a new task.
        
        Args:
            request: The task creation request.
            
        Returns:
            The task creation response.
        """
        # Create a task ID
        task_id = f"TASK-{str(uuid.uuid4())[:8]}"
        
        # Convert string values to enums
        try:
            priority = TaskPriority(request.priority)
        except ValueError:
            priority = TaskPriority.MEDIUM
            
        try:
            task_type = TaskType(request.task_type)
        except ValueError:
            task_type = TaskType.FEATURE
        
        # Create the task
        task = Task(
            id=task_id,
            title=request.title,
            description=request.description,
            task_type=task_type,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        
        self.tasks_store[task_id] = task
        
        return CreateTaskResponse(
            task_id=task_id,
            status="Task created successfully"
        )
        
    async def api_assign_task(self, request: AssignTaskRequest = Body(...)) -> AssignTaskResponse:
        """API endpoint to assign a task to an agent.
        
        Args:
            request: The task assignment request.
            
        Returns:
            The task assignment response.
        """
        # Validate task exists
        if request.task_id not in self.tasks_store:
            raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found.")
            
        task = self.tasks_store[request.task_id]
        
        # If a specific agent was requested, use that
        agent_id = request.agent_id
        
        # Otherwise find the most suitable agent
        if not agent_id:
            # Filter by agent type (engineers)
            suitable_agents = []
            for a_id, load in self.agent_loads.items():
                if load.agent_type == "engineer":
                    suitable_agents.append((a_id, load))
                    
            if not suitable_agents:
                return AssignTaskResponse(
                    status="No suitable engineers available.",
                    assigned_to=None
                )
                
            # Find the agent with the lowest load
            agent_id, _ = min(suitable_agents, key=lambda x: x[1].load_percentage)
            
        # Update task and agent
        task.assigned_to = agent_id
        task.status = TaskStatus.IN_PROGRESS
        task.updated_at = datetime.now()
        
        self.tasks_store[request.task_id] = task
        self.agent_loads[agent_id].current_tasks += 1
        
        return AssignTaskResponse(
            status=f"Task {request.task_id} assigned to {agent_id}.",
            assigned_to=agent_id
        )
        
    async def api_list_tasks(self, request: ListTasksRequest = Body(...)) -> ListTasksResponse:
        """API endpoint to list tasks with optional status filtering.
        
        Args:
            request: The list tasks request.
            
        Returns:
            The list tasks response.
        """
        tasks = []
        
        for task_id, task in self.tasks_store.items():
            # Apply status filter if provided
            if request.status:
                try:
                    status_enum = TaskStatus(request.status)
                    if task.status != status_enum:
                        continue
                except ValueError:
                    # Invalid status, ignore filter
                    pass
                    
            # Add task to list
            tasks.append(TaskInfo(
                id=task.id,
                title=task.title,
                status=task.status.value,
                priority=task.priority.value,
                assigned_to=task.assigned_to
            ))
            
        return ListTasksResponse(tasks=tasks)
        
    async def api_review_task(self, request: ReviewTaskRequest = Body(...)) -> ReviewTaskResponse:
        """API endpoint to review a completed or tested task.
        
        Args:
            request: The review task request.
            
        Returns:
            The review task response.
        """
        # Validate task exists
        if request.task_id not in self.tasks_store:
            raise HTTPException(status_code=404, detail=f"Task {request.task_id} not found.")
            
        task = self.tasks_store[request.task_id]
        
        # Verify task is in a reviewable state
        if task.status not in [TaskStatus.COMPLETED, TaskStatus.TESTING]:
            return ReviewTaskResponse(
                status=f"Task {request.task_id} is not ready for review (Status: {task.status.value})",
                new_task_status=task.status.value
            )
            
        # Update task status based on approval
        if request.approve:
            task.status = TaskStatus.APPROVED
            message = f"Task {request.task_id} has been approved."
        else:
            task.status = TaskStatus.REJECTED
            message = f"Task {request.task_id} has been rejected."
            
        task.updated_at = datetime.now()
        
        # Add comment if provided
        if request.comment:
            task.comments.append(f"[{datetime.now()}] {self.name}: {request.comment}")
            
        # Handle rejected tasks
        if not request.approve:
            task.status = TaskStatus.PENDING
            if task.assigned_to:
                self.agent_loads[task.assigned_to].current_tasks -= 1
                task.assigned_to = None
                
        # Handle approved tasks that were in testing
        if request.approve and task.status == TaskStatus.TESTING:
            for agent_id, load in self.agent_loads.items():
                if load.agent_type == "tester" and task.assigned_to == agent_id:
                    load.current_tasks -= 1
                    break
                    
        self.tasks_store[request.task_id] = task
        
        return ReviewTaskResponse(
            status=message,
            new_task_status=task.status.value
        )
        
    async def api_get_agent_status(self, request: dict = Body(...)) -> GetAgentStatusResponse:
        """API endpoint to get a status report on all agents.
        
        Args:
            request: Empty request.
            
        Returns:
            The agent status response.
        """
        agents = []
        
        for agent_id, load in self.agent_loads.items():
            agents.append(AgentStatusResponse(
                agent_id=agent_id,
                agent_type=load.agent_type,
                current_tasks=load.current_tasks,
                max_capacity=load.max_capacity,
                load_percentage=load.load_percentage
            ))
            
        return GetAgentStatusResponse(agents=agents)
