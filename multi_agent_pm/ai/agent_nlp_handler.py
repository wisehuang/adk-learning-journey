"""Natural language processing handler for agent commands.

This module provides functionality to bridge natural language commands
with the agent API methods using Google Gemini.
"""

import logging
from typing import Dict, List, Any, Optional, Callable, TypeVar, Awaitable

from .gemini_client import GeminiClient
from ..common import Task, TaskStatus, AgentLoad

# Type variables for type hinting
T = TypeVar('T')
AsyncMethod = Callable[..., Awaitable[T]]

# Configure logging
logger = logging.getLogger(__name__)

class AgentNLPHandler:
    """Handler for natural language processing of agent commands."""
    
    def __init__(self, agent_type: str, api_key: Optional[str] = None):
        """Initialize the NLP handler.
        
        Args:
            agent_type: The type of agent ("manager", "engineer", "tester").
            api_key: Optional Gemini API key.
        """
        self.agent_type = agent_type
        self.gemini_client = GeminiClient(api_key)
        self.method_mapping: Dict[str, str] = {}
        self._setup_method_mapping()
        
    def _setup_method_mapping(self):
        """Set up mapping between operation names and method names."""
        # Common prefix for API methods
        prefix = "api_"
        
        # Manager agent methods
        if self.agent_type == "manager":
            self.method_mapping = {
                "create_task": f"{prefix}create_task",
                "assign_task": f"{prefix}assign_task",
                "list_tasks": f"{prefix}list_tasks",
                "review_task": f"{prefix}review_task",
                "get_agent_status": f"{prefix}get_agent_status"
            }
        
        # Engineer agent methods
        elif self.agent_type == "engineer":
            self.method_mapping = {
                "list_my_tasks": f"{prefix}list_my_tasks",
                "work_on_task": f"{prefix}work_on_task",
                "complete_task": f"{prefix}complete_task",
                "get_status": f"{prefix}get_status"
            }
        
        # Tester agent methods
        elif self.agent_type == "tester":
            self.method_mapping = {
                "list_completed_tasks": f"{prefix}list_completed_tasks",
                "list_my_tasks": f"{prefix}list_my_tasks",
                "test_task": f"{prefix}test_task",
                "submit_test_results": f"{prefix}submit_test_results",
                "get_status": f"{prefix}get_status"
            }
    
    async def process_command(self, 
                        agent: Any, 
                        command_text: str, 
                        context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Process a natural language command and execute the appropriate agent method.
        
        Args:
            agent: The agent instance.
            command_text: The natural language command text.
            context: Optional context information to help with understanding.
            
        Returns:
            The result of the agent API call.
        """
        # Provide default context if none is provided
        if context is None:
            context = {}
        
        # Add agent-specific context
        context.update(self._get_agent_context(agent))
        
        # Use Gemini to understand the command
        cmd_info = await self.gemini_client.understand_command(
            command_text, 
            self.agent_type,
            context
        )
        
        logger.info(f"Processed command: {command_text} → {cmd_info['operation']}")
        
        # Map operation to method name
        method_name = self.method_mapping.get(cmd_info['operation'])
        
        if not method_name or not hasattr(agent, method_name):
            logger.warning(f"Unknown operation: {cmd_info['operation']}")
            return {"error": f"Unknown operation: {cmd_info['operation']}"}
        
        # Get the method and call it with parameters
        method = getattr(agent, method_name)
        
        try:
            # Convert parameters to the correct format for the API method
            formatted_params = self._format_parameters(cmd_info['parameters'], method_name)
            
            # Call the method
            result = await method(**formatted_params)
            return result
        except Exception as e:
            logger.error(f"Error calling {method_name}: {str(e)}")
            return {"error": str(e)}
    
    def _get_agent_context(self, agent: Any) -> Dict[str, Any]:
        """Get context information from the agent to help with command understanding.
        
        Args:
            agent: The agent instance.
            
        Returns:
            A dictionary with context information.
        """
        context = {
            "agent_type": self.agent_type,
            "agent_name": getattr(agent, "name", "unknown")
        }
        
        # Add agent-specific context
        if hasattr(agent, "tasks_store"):
            # Count tasks by status
            status_counts = {}
            for task in agent.tasks_store.values():
                status = str(task.status)
                status_counts[status] = status_counts.get(status, 0) + 1
            
            context["task_counts"] = status_counts
        
        # Add agent load if available
        if hasattr(agent, "agent_loads") and hasattr(agent, "name"):
            agent_load = agent.agent_loads.get(agent.name)
            if agent_load:
                context["current_load"] = agent_load.load_percentage
        
        return context
    
    def _format_parameters(self, params: Dict[str, Any], method_name: str) -> Dict[str, Any]:
        """Format parameters for the API method call.
        
        Args:
            params: The parameters from the Gemini response.
            method_name: The method name being called.
            
        Returns:
            Formatted parameters.
        """
        # Handle specific parameter formatting needs based on method
        
        # For create_task, we need to convert the parameters to the request object
        if method_name == "api_create_task":
            # Import here to avoid circular imports
            from ..agents.manager.agent import CreateTaskRequest
            
            if not all(k in params for k in ["title", "description"]):
                raise ValueError("Missing required parameters for create_task: title, description")
                
            return {
                "request": CreateTaskRequest(
                    title=params.get("title", "Untitled Task"),
                    description=params.get("description", "No description provided"),
                    priority=params.get("priority", "medium"),
                    task_type=params.get("task_type", "feature")
                )
            }
            
        # For assign_task, we need the task_id and optional agent_id
        elif method_name == "api_assign_task":
            from ..agents.manager.agent import AssignTaskRequest
            
            if "task_id" not in params:
                raise ValueError("Missing required parameter for assign_task: task_id")
                
            return {
                "request": AssignTaskRequest(
                    task_id=params["task_id"],
                    agent_id=params.get("agent_id")
                )
            }
            
        # For review_task, we need the task_id and approve flag
        elif method_name == "api_review_task":
            from ..agents.manager.agent import ReviewTaskRequest
            
            if "task_id" not in params:
                raise ValueError("Missing required parameter for review_task: task_id")
                
            return {
                "request": ReviewTaskRequest(
                    task_id=params["task_id"],
                    approve=params.get("approve", True),
                    comment=params.get("comment")
                )
            }
            
        # For all other methods, just pass the parameters directly
        return params 