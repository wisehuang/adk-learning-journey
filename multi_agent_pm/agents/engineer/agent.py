"""Engineer agent implementation for the project management system.

The Engineer agent is responsible for:
1. Implementation of assigned tasks
2. Reporting task progress
3. Code and technical development
4. Completing tasks for review
"""

import time
import random
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.tools import FunctionTool
from pydantic import BaseModel as PydanticBaseModel, ConfigDict
from fastapi import FastAPI, HTTPException, Body

from ...common import Task, TaskStatus, AgentLoad, get_timestamp


# FastAPI models for request/response
class ListMyTasksResponse(PydanticBaseModel):
    """Response model for listing tasks."""
    tasks: List[Dict[str, Any]]

class WorkOnTaskRequest(PydanticBaseModel):
    """Request model for working on a task."""
    task_id: str

class WorkOnTaskResponse(PydanticBaseModel):
    """Response model for working on a task."""
    status: str
    message: str

class CompleteTaskRequest(PydanticBaseModel):
    """Request model for completing a task."""
    task_id: str
    comment: Optional[str] = None

class CompleteTaskResponse(PydanticBaseModel):
    """Response model for completing a task."""
    status: str
    message: str
    available_testers: List[str]

class GetStatusResponse(PydanticBaseModel):
    """Response model for getting engineer status."""
    name: str
    current_tasks: int
    max_capacity: int
    load_percentage: float
    assigned_tasks: List[Dict[str, Any]]


class EngineerAgent(BaseAgent):
    """Engineer agent for the project management system."""
    
    # Add model_config to allow arbitrary attributes when Pydantic v2 is used
    model_config = ConfigDict(extra="allow")
    
    # OR uncomment these for Pydantic v1 if ConfigDict doesn't work
    # class Config:
    #     extra = "allow"
    
    def __init__(self, name: str, tasks_store: Dict[str, Task], agent_loads: Dict[str, AgentLoad]):
        """Initialize the Engineer agent.
        
        Args:
            name: The name of the agent.
            tasks_store: Reference to the shared tasks store.
            agent_loads: Reference to the agent load information.
        """
        super().__init__(name=name)
        self.tasks_store = tasks_store
        self.agent_loads = agent_loads
        
        # Create API app
        self.app = FastAPI(title=f"{name} API")
        self._setup_routes()
        
    def _setup_routes(self):
        """Set up the API routes for the engineer agent."""
        # Load agent manifest
        manifest_path = os.path.join(os.path.dirname(__file__), ".well-known", "agent.json")
        try:
            with open(manifest_path, "r") as f:
                self.manifest = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load agent manifest: {e}")
            self.manifest = {}
        
        # Set up routes based on capabilities
        self.app.post("/api/agents/engineer/list_my_tasks")(self.api_list_my_tasks)
        self.app.post("/api/agents/engineer/work_on_task")(self.api_work_on_task)
        self.app.post("/api/agents/engineer/complete_task")(self.api_complete_task)
        self.app.post("/api/agents/engineer/get_status")(self.api_get_status)
        
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the Engineer agent's async implementation.
        
        This is the main entry point for the Engineer agent.
        
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
        
        # Process user command
        if "my tasks" in user_input.lower():
            tasks_list = self.list_my_tasks()
            yield Event(
                author=self.name,
                content=tasks_list
            )
            
        elif "work on" in user_input.lower():
            work_result = await self.work_on_task(ctx, user_input)
            yield Event(
                author=self.name,
                content=work_result
            )
            
        elif "complete task" in user_input.lower():
            completion_result = await self.complete_task(ctx, user_input)
            yield Event(
                author=self.name,
                content=completion_result
            )
            
        elif "status" in user_input.lower():
            status = self.get_status()
            yield Event(
                author=self.name,
                content=status
            )
            
        else:
            yield Event(
                author=self.name,
                content=(
                    f"I'm {self.name}, an engineer. I can help with: "
                    "my tasks, work on [task-id], complete task [task-id], status"
                )
            )

    def list_my_tasks(self) -> str:
        """List all tasks assigned to this engineer.
        
        Returns:
            A formatted string with the task list.
        """
        my_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name:
                my_tasks.append(task)
                
        if not my_tasks:
            return f"No tasks currently assigned to {self.name}."
            
        result = f"Tasks assigned to {self.name}:\n"
        for task in my_tasks:
            result += (
                f"- {task.id}: {task.title} [{task.status}] "
                f"Priority: {task.priority} | Type: {task.task_type}\n"
            )
            
        return result

    async def work_on_task(self, ctx: InvocationContext, user_input: str) -> str:
        """Work on an assigned task.
        
        Args:
            ctx: The invocation context.
            user_input: The user input containing task details.
            
        Returns:
            A string with the work result.
        """
        # Extract task ID from input
        parts = user_input.lower().split()
        task_id = None
        for part in parts:
            if part.startswith("task-"):
                task_id = part.upper()
                break
                
        if not task_id:
            return "Please specify a task ID to work on (e.g., TASK-12345678)"
            
        if task_id not in self.tasks_store:
            return f"Task {task_id} not found."
            
        task = self.tasks_store[task_id]
        
        if task.assigned_to != self.name:
            return f"Task {task_id} is not assigned to me."
            
        if task.status != TaskStatus.IN_PROGRESS:
            return f"Task {task_id} is not in progress (Status: {task.status.value})"
            
        # Simulate working on the task
        work_message = f"Working on task {task_id}: {task.title}...\n"
        
        # Add a comment to the task
        timestamp = get_timestamp()
        task.comments.append(f"[{timestamp}] {self.name}: Working on implementation.")
        
        # Update task status to indicate active work
        task.updated_at = datetime.now()
        self.tasks_store[task_id] = task
        
        work_message += f"Progress update added to task {task_id}."
        return work_message

    async def complete_task(self, ctx: InvocationContext, user_input: str) -> str:
        """Mark a task as completed.
        
        Args:
            ctx: The invocation context.
            user_input: The user input containing task details.
            
        Returns:
            A string with the completion result.
        """
        # Extract task ID from input
        parts = user_input.lower().split()
        task_id = None
        for part in parts:
            if part.startswith("task-"):
                task_id = part.upper()
                break
                
        if not task_id:
            return "Please specify a task ID to complete (e.g., TASK-12345678)"
            
        if task_id not in self.tasks_store:
            return f"Task {task_id} not found."
            
        task = self.tasks_store[task_id]
        
        if task.assigned_to != self.name:
            return f"Task {task_id} is not assigned to me."
            
        if task.status != TaskStatus.IN_PROGRESS:
            return f"Task {task_id} is not in progress (Status: {task.status.value})"
            
        # Mark the task as completed
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now()
        
        # Add a completion comment
        timestamp = get_timestamp()
        task.comments.append(f"[{timestamp}] {self.name}: Task implementation completed.")
        
        self.tasks_store[task_id] = task
        
        # Check for available testers
        available_testers = []
        for agent_id, load in self.agent_loads.items():
            if load.agent_type == "tester" and load.available_capacity > 0:
                available_testers.append((agent_id, load))
                
        # If testers available, suggest testing
        suggestion = ""
        if available_testers:
            suggestion = "\nTask is ready for testing."
            
        return f"Task {task_id} marked as completed.{suggestion}"

    def get_status(self) -> str:
        """Get the current status of this engineer.
        
        Returns:
            A string with the status information.
        """
        my_load = self.agent_loads.get(self.name)
        if not my_load:
            return f"Status information not available for {self.name}."
            
        assigned_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name:
                assigned_tasks.append(task)
                
        status = f"Status for {self.name}:\n"
        status += f"- Current load: {my_load.current_tasks}/{my_load.max_capacity} tasks ({my_load.load_percentage:.1f}%)\n"
        status += f"- Tasks in progress: {len(assigned_tasks)}\n"
        
        if assigned_tasks:
            status += "- Assigned tasks:\n"
            for task in assigned_tasks:
                status += f"  * {task.id}: {task.title} [{task.status}]\n"
                
        return status

    # API implementations matching the agent.json capabilities
    async def api_list_my_tasks(self, request: dict = Body(...)) -> ListMyTasksResponse:
        """API endpoint to list tasks assigned to this engineer.
        
        Args:
            request: Empty request.
            
        Returns:
            The list tasks response.
        """
        my_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name:
                my_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "task_type": task.task_type.value
                })
                
        return ListMyTasksResponse(tasks=my_tasks)
        
    async def api_work_on_task(self, request: WorkOnTaskRequest = Body(...)) -> WorkOnTaskResponse:
        """API endpoint to work on an assigned task.
        
        Args:
            request: The work on task request.
            
        Returns:
            The work on task response.
        """
        task_id = request.task_id
        
        if task_id not in self.tasks_store:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
            
        task = self.tasks_store[task_id]
        
        if task.assigned_to != self.name:
            raise HTTPException(status_code=403, detail=f"Task {task_id} is not assigned to me.")
            
        if task.status != TaskStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=400, 
                detail=f"Task {task_id} is not in progress (Status: {task.status.value})"
            )
            
        # Add a comment to the task
        timestamp = get_timestamp()
        task.comments.append(f"[{timestamp}] {self.name}: Working on implementation.")
        
        # Update task status to indicate active work
        task.updated_at = datetime.now()
        self.tasks_store[task_id] = task
        
        return WorkOnTaskResponse(
            status="success",
            message=f"Progress update added to task {task_id}."
        )
        
    async def api_complete_task(self, request: CompleteTaskRequest = Body(...)) -> CompleteTaskResponse:
        """API endpoint to mark a task as completed.
        
        Args:
            request: The complete task request.
            
        Returns:
            The complete task response.
        """
        task_id = request.task_id
        
        if task_id not in self.tasks_store:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
            
        task = self.tasks_store[task_id]
        
        if task.assigned_to != self.name:
            raise HTTPException(status_code=403, detail=f"Task {task_id} is not assigned to me.")
            
        if task.status != TaskStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=400, 
                detail=f"Task {task_id} is not in progress (Status: {task.status.value})"
            )
            
        # Mark the task as completed
        task.status = TaskStatus.COMPLETED
        task.updated_at = datetime.now()
        
        # Add a completion comment
        timestamp = get_timestamp()
        comment = request.comment if request.comment else "Task implementation completed."
        task.comments.append(f"[{timestamp}] {self.name}: {comment}")
        
        self.tasks_store[task_id] = task
        
        # Check for available testers
        available_testers = []
        for agent_id, load in self.agent_loads.items():
            if load.agent_type == "tester" and load.available_capacity > 0:
                available_testers.append(agent_id)
                
        return CompleteTaskResponse(
            status="success",
            message=f"Task {task_id} marked as completed.",
            available_testers=available_testers
        )
        
    async def api_get_status(self, request: dict = Body(...)) -> GetStatusResponse:
        """API endpoint to get the current status of this engineer.
        
        Args:
            request: Empty request.
            
        Returns:
            The engineer status response.
        """
        my_load = self.agent_loads.get(self.name)
        if not my_load:
            raise HTTPException(status_code=404, detail=f"Status information not available for {self.name}.")
            
        assigned_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name:
                assigned_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value
                })
                
        return GetStatusResponse(
            name=self.name,
            current_tasks=my_load.current_tasks,
            max_capacity=my_load.max_capacity,
            load_percentage=my_load.load_percentage,
            assigned_tasks=assigned_tasks
        )
