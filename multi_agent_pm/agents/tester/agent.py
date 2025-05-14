"""Tester agent implementation for the project management system.

The Tester agent is responsible for:
1. Testing completed tasks
2. Reporting test results
3. Validating quality standards
4. Pass/fail determination
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
class ListCompletedTasksResponse(PydanticBaseModel):
    """Response model for listing completed tasks."""
    tasks: List[Dict[str, Any]]

class ListMyTasksResponse(PydanticBaseModel):
    """Response model for listing my tasks."""
    tasks: List[Dict[str, Any]]

class TestTaskRequest(PydanticBaseModel):
    """Request model for testing a task."""
    task_id: str

class TestTaskResponse(PydanticBaseModel):
    """Response model for testing a task."""
    status: str
    message: str

class SubmitTestResultsRequest(PydanticBaseModel):
    """Request model for submitting test results."""
    task_id: str
    passed: bool
    notes: Optional[str] = None

class SubmitTestResultsResponse(PydanticBaseModel):
    """Response model for submitting test results."""
    status: str
    message: str

class GetStatusResponse(PydanticBaseModel):
    """Response model for getting tester status."""
    name: str
    current_tasks: int
    max_capacity: int
    load_percentage: float
    testing_tasks: List[Dict[str, Any]]


class TesterAgent(BaseAgent):
    """Tester agent for the project management system."""
    
    # Add model_config to allow arbitrary attributes when Pydantic v2 is used
    model_config = ConfigDict(extra="allow")
    
    # OR uncomment these for Pydantic v1 if ConfigDict doesn't work
    # class Config:
    #     extra = "allow"
    
    def __init__(self, name: str, tasks_store: Dict[str, Task], agent_loads: Dict[str, AgentLoad]):
        """Initialize the Tester agent.
        
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
        """Set up the API routes for the tester agent."""
        # Load agent manifest
        manifest_path = os.path.join(os.path.dirname(__file__), ".well-known", "agent.json")
        try:
            with open(manifest_path, "r") as f:
                self.manifest = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logging.error(f"Failed to load agent manifest: {e}")
            self.manifest = {}
        
        # Set up routes based on capabilities
        self.app.post("/api/agents/tester/list_completed_tasks")(self.api_list_completed_tasks)
        self.app.post("/api/agents/tester/list_my_tasks")(self.api_list_my_tasks)
        self.app.post("/api/agents/tester/test_task")(self.api_test_task)
        self.app.post("/api/agents/tester/submit_test_results")(self.api_submit_test_results)
        self.app.post("/api/agents/tester/get_status")(self.api_get_status)
        
    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Run the Tester agent's async implementation.
        
        This is the main entry point for the Tester agent.
        
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
        if "completed tasks" in user_input.lower():
            tasks_list = self.list_completed_tasks()
            yield Event(
                author=self.name,
                content=tasks_list
            )
            
        elif "test task" in user_input.lower():
            test_result = await self.test_task(ctx, user_input)
            yield Event(
                author=self.name,
                content=test_result
            )
            
        elif "my tasks" in user_input.lower():
            tasks_list = self.list_my_tasks()
            yield Event(
                author=self.name,
                content=tasks_list
            )
            
        elif "submit test results" in user_input.lower():
            submission_result = await self.submit_test_results(ctx, user_input)
            yield Event(
                author=self.name,
                content=submission_result
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
                    f"I'm {self.name}, a tester. I can help with: "
                    "completed tasks, test task [task-id], my tasks, "
                    "submit test results [task-id], status"
                )
            )

    def list_completed_tasks(self) -> str:
        """List all tasks with COMPLETED status.
        
        Returns:
            A formatted string with the completed task list.
        """
        completed_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.status == TaskStatus.COMPLETED:
                completed_tasks.append(task)
                
        if not completed_tasks:
            return "No tasks currently in COMPLETED status."
            
        result = "Tasks ready for testing:\n"
        for task in completed_tasks:
            result += (
                f"- {task.id}: {task.title} [{task.status}] "
                f"Priority: {task.priority} | Type: {task.task_type}\n"
            )
            
        return result

    def list_my_tasks(self) -> str:
        """List all tasks assigned to this tester.
        
        Returns:
            A formatted string with the task list.
        """
        my_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name and task.status == TaskStatus.TESTING:
                my_tasks.append(task)
                
        if not my_tasks:
            return f"No tasks currently assigned to {self.name} for testing."
            
        result = f"Tasks assigned to {self.name} for testing:\n"
        for task in my_tasks:
            result += (
                f"- {task.id}: {task.title} [{task.status}] "
                f"Priority: {task.priority} | Type: {task.task_type}\n"
            )
            
        return result

    async def test_task(self, ctx: InvocationContext, user_input: str) -> str:
        """Start testing a completed task.
        
        Args:
            ctx: The invocation context.
            user_input: The user input containing task details.
            
        Returns:
            A string with the test result.
        """
        # Extract task ID from input
        parts = user_input.lower().split()
        task_id = None
        for part in parts:
            if part.startswith("task-"):
                task_id = part.upper()
                break
                
        if not task_id:
            return "Please specify a task ID to test (e.g., TASK-12345678)"
            
        if task_id not in self.tasks_store:
            return f"Task {task_id} not found."
            
        task = self.tasks_store[task_id]
        
        if task.status != TaskStatus.COMPLETED:
            return f"Task {task_id} is not ready for testing (Status: {task.status.value})"
            
        # Check if the tester has capacity
        my_load = self.agent_loads.get(self.name)
        if not my_load:
            return f"Load information not available for {self.name}."
            
        if my_load.available_capacity <= 0:
            return f"Cannot take on more testing tasks. Current load: {my_load.current_tasks}/{my_load.max_capacity}."
            
        # Assign task to this tester
        task.assigned_to = self.name
        task.status = TaskStatus.TESTING
        task.updated_at = datetime.now()
        
        # Add a comment to the task
        timestamp = get_timestamp()
        task.comments.append(f"[{timestamp}] {self.name}: Starting testing process.")
        
        self.tasks_store[task_id] = task
        self.agent_loads[self.name].current_tasks += 1
        
        return f"Task {task_id} assigned to {self.name} for testing."

    async def submit_test_results(self, ctx: InvocationContext, user_input: str) -> str:
        """Submit test results for a task.
        
        Args:
            ctx: The invocation context.
            user_input: The user input containing task details.
            
        Returns:
            A string with the submission result.
        """
        # Extract task ID from input
        parts = user_input.lower().split()
        task_id = None
        for part in parts:
            if part.startswith("task-"):
                task_id = part.upper()
                break
                
        if not task_id:
            return "Please specify a task ID to submit results for (e.g., TASK-12345678)"
            
        if task_id not in self.tasks_store:
            return f"Task {task_id} not found."
            
        task = self.tasks_store[task_id]
        
        if task.assigned_to != self.name:
            return f"Task {task_id} is not assigned to me for testing."
            
        if task.status != TaskStatus.TESTING:
            return f"Task {task_id} is not in testing status (Status: {task.status.value})"
            
        # Check if the test passed or failed based on user input
        test_passed = True
        for part in parts:
            if part in ["fail", "failed", "failing"]:
                test_passed = False
                break
                
        # Generate test results
        timestamp = get_timestamp()
        test_results = {
            "tester": self.name,
            "timestamp": timestamp,
            "status": "passed" if test_passed else "failed",
            "notes": f"Test {'passed' if test_passed else 'failed'} by {self.name}"
        }
        
        # Update task
        task.test_results = test_results
        if test_passed:
            task.comments.append(f"[{timestamp}] {self.name}: Testing completed - PASSED")
        else:
            task.comments.append(f"[{timestamp}] {self.name}: Testing completed - FAILED")
            
        task.updated_at = datetime.now()
        
        # Keep the task in TESTING status for manager review
        self.tasks_store[task_id] = task
        
        return (
            f"Test results submitted for task {task_id}: "
            f"{'PASSED' if test_passed else 'FAILED'}. "
            f"Task is ready for manager review."
        )

    def get_status(self) -> str:
        """Get the current status of this tester.
        
        Returns:
            A string with the status information.
        """
        my_load = self.agent_loads.get(self.name)
        if not my_load:
            return f"Status information not available for {self.name}."
            
        testing_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name and task.status == TaskStatus.TESTING:
                testing_tasks.append(task)
                
        status = f"Status for {self.name}:\n"
        status += f"- Current load: {my_load.current_tasks}/{my_load.max_capacity} tasks ({my_load.load_percentage:.1f}%)\n"
        status += f"- Tasks in testing: {len(testing_tasks)}\n"
        
        if testing_tasks:
            status += "- Testing tasks:\n"
            for task in testing_tasks:
                status += f"  * {task.id}: {task.title}\n"
                
        return status

    # API implementations matching the agent.json capabilities
    async def api_list_completed_tasks(self, request: dict = Body(...)) -> ListCompletedTasksResponse:
        """API endpoint to list all tasks with COMPLETED status.
        
        Args:
            request: Empty request.
            
        Returns:
            The list completed tasks response.
        """
        completed_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.status == TaskStatus.COMPLETED:
                completed_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "task_type": task.task_type.value,
                    "assigned_to": task.assigned_to
                })
                
        return ListCompletedTasksResponse(tasks=completed_tasks)
        
    async def api_list_my_tasks(self, request: dict = Body(...)) -> ListMyTasksResponse:
        """API endpoint to list all tasks assigned to this tester.
        
        Args:
            request: Empty request.
            
        Returns:
            The list my tasks response.
        """
        my_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name and task.status == TaskStatus.TESTING:
                my_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value,
                    "priority": task.priority.value,
                    "task_type": task.task_type.value
                })
                
        return ListMyTasksResponse(tasks=my_tasks)
        
    async def api_test_task(self, request: TestTaskRequest = Body(...)) -> TestTaskResponse:
        """API endpoint to start testing a completed task.
        
        Args:
            request: The test task request.
            
        Returns:
            The test task response.
        """
        task_id = request.task_id
        
        if task_id not in self.tasks_store:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
            
        task = self.tasks_store[task_id]
        
        if task.status != TaskStatus.COMPLETED:
            raise HTTPException(
                status_code=400, 
                detail=f"Task {task_id} is not ready for testing (Status: {task.status.value})"
            )
            
        # Check if the tester has capacity
        my_load = self.agent_loads.get(self.name)
        if not my_load:
            raise HTTPException(status_code=404, detail=f"Load information not available for {self.name}.")
            
        if my_load.available_capacity <= 0:
            raise HTTPException(
                status_code=400, 
                detail=f"Cannot take on more testing tasks. Current load: {my_load.current_tasks}/{my_load.max_capacity}."
            )
            
        # Assign task to this tester
        task.assigned_to = self.name
        task.status = TaskStatus.TESTING
        task.updated_at = datetime.now()
        
        # Add a comment to the task
        timestamp = get_timestamp()
        task.comments.append(f"[{timestamp}] {self.name}: Starting testing process.")
        
        self.tasks_store[task_id] = task
        self.agent_loads[self.name].current_tasks += 1
        
        return TestTaskResponse(
            status="success",
            message=f"Task {task_id} assigned to {self.name} for testing."
        )
        
    async def api_submit_test_results(self, request: SubmitTestResultsRequest = Body(...)) -> SubmitTestResultsResponse:
        """API endpoint to submit test results for a task.
        
        Args:
            request: The submit test results request.
            
        Returns:
            The submit test results response.
        """
        task_id = request.task_id
        
        if task_id not in self.tasks_store:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found.")
            
        task = self.tasks_store[task_id]
        
        if task.assigned_to != self.name:
            raise HTTPException(status_code=403, detail=f"Task {task_id} is not assigned to me for testing.")
            
        if task.status != TaskStatus.TESTING:
            raise HTTPException(
                status_code=400, 
                detail=f"Task {task_id} is not in testing status (Status: {task.status.value})"
            )
            
        # Generate test results
        timestamp = get_timestamp()
        test_results = {
            "tester": self.name,
            "timestamp": timestamp,
            "status": "passed" if request.passed else "failed",
            "notes": request.notes or f"Test {'passed' if request.passed else 'failed'} by {self.name}"
        }
        
        # Update task
        task.test_results = test_results
        if request.passed:
            task.comments.append(f"[{timestamp}] {self.name}: Testing completed - PASSED")
        else:
            task.comments.append(f"[{timestamp}] {self.name}: Testing completed - FAILED")
            
        task.updated_at = datetime.now()
        
        # Keep the task in TESTING status for manager review
        self.tasks_store[task_id] = task
        
        return SubmitTestResultsResponse(
            status="success",
            message=f"Test results submitted for task {task_id}: {'PASSED' if request.passed else 'FAILED'}. Task is ready for manager review."
        )
        
    async def api_get_status(self, request: dict = Body(...)) -> GetStatusResponse:
        """API endpoint to get the current status of this tester.
        
        Args:
            request: Empty request.
            
        Returns:
            The tester status response.
        """
        my_load = self.agent_loads.get(self.name)
        if not my_load:
            raise HTTPException(status_code=404, detail=f"Status information not available for {self.name}.")
            
        testing_tasks = []
        for task_id, task in self.tasks_store.items():
            if task.assigned_to == self.name and task.status == TaskStatus.TESTING:
                testing_tasks.append({
                    "id": task.id,
                    "title": task.title,
                    "status": task.status.value
                })
                
        return GetStatusResponse(
            name=self.name,
            current_tasks=my_load.current_tasks,
            max_capacity=my_load.max_capacity,
            load_percentage=my_load.load_percentage,
            testing_tasks=testing_tasks
        )
