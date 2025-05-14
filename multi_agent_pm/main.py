"""Main entry point for the multi-agent project management system.

This module initializes the workflow and provides functions to run the system.
"""

import asyncio
import logging
import threading
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
import uvicorn
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path('.') / '.env'
    # Check if .env file exists, otherwise use template
    if not env_path.exists():
        template_path = Path('.') / '.env-template'
        if template_path.exists():
            logger.warning(f".env file not found. Please copy .env-template to .env and configure it.")
    load_dotenv(dotenv_path=env_path)
except ImportError:
    logger.warning("python-dotenv not installed. Environment variables will only be loaded from system.")

from google.adk.runners import Runner
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents import BaseAgent

# Use relative imports for running as a module
from .workflow.coordinator import WorkflowCoordinator
from .common import Task, TaskStatus, AgentLoad
from .ai import AgentNLPHandler


def setup_system() -> WorkflowCoordinator:
    """Set up the multi-agent project management system.
    
    Returns:
        A configured WorkflowCoordinator instance.
    """
    logger.info("Setting up multi-agent project management system...")
    coordinator = WorkflowCoordinator()
    
    # Preload some sample tasks for demonstration
    preload_sample_tasks(coordinator)
    
    logger.info("System setup complete")
    return coordinator


def preload_sample_tasks(coordinator: WorkflowCoordinator) -> None:
    """Preload sample tasks for demonstration.
    
    Args:
        coordinator: The workflow coordinator instance.
    """
    logger.info("Preloading sample tasks...")
    
    # Create sample tasks
    sample_tasks = [
        {
            "id": "TASK-12345678",
            "title": "Implement user authentication feature",
            "description": "Create a secure authentication system for user login with JWT",
            "task_type": TaskStatus.PENDING,
            "priority": "high"
        },
        {
            "id": "TASK-23456789",
            "title": "Fix pagination bug in search results",
            "description": "The pagination links on search results page are not working correctly",
            "task_type": TaskStatus.PENDING,
            "priority": "medium"
        },
        {
            "id": "TASK-34567890",
            "title": "Add product sorting functionality",
            "description": "Implement sorting of products by price, rating, and newest",
            "task_type": TaskStatus.PENDING,
            "priority": "low"
        }
    ]
    
    # Use the manager agent to create the sample tasks
    asyncio.run(create_sample_tasks(coordinator, sample_tasks))
    
    logger.info(f"Preloaded {len(sample_tasks)} sample tasks")


async def create_sample_tasks(coordinator: WorkflowCoordinator, task_data: List[Dict[str, Any]]) -> None:
    """Asynchronously create sample tasks using the manager agent.
    
    Args:
        coordinator: The workflow coordinator instance.
        task_data: List of task data dictionaries.
    """
    # Use the manager agent directly to create tasks
    manager = coordinator.manager
    
    # Import the request class with correct package-relative import
    from .agents.manager.agent import CreateTaskRequest
    
    for task in task_data:
        # Create a request object for the API
        request = CreateTaskRequest(
            title=task["title"],
            description=task["description"],
            priority=task.get("priority", "medium"),
            task_type=task.get("task_type", "feature")
        )
        
        # Call the API method directly
        await manager.api_create_task(request)
        
    logger.info(f"Created {len(task_data)} sample tasks")


async def rebalance_periodically(coordinator: WorkflowCoordinator, interval_seconds: int = 60) -> None:
    """Periodically rebalance workload among agents.
    
    Args:
        coordinator: The workflow coordinator instance.
        interval_seconds: Time interval between rebalancing in seconds.
    """
    logger.info(f"Starting periodic workload rebalancing every {interval_seconds} seconds")
    
    while True:
        # Wait for the specified interval
        await asyncio.sleep(interval_seconds)
        
        # Rebalance workload
        logger.info("Rebalancing workload...")
        updated_loads = coordinator.rebalance_workload()
        
        # Log the rebalancing results
        for agent_id, load in updated_loads.items():
            logger.info(f"Agent {agent_id}: {load.current_tasks}/{load.max_capacity} tasks ({load.load_percentage:.1f}% load)")


def run_api_server(app, host: str, port: int, agent_name: str) -> None:
    """Run a FastAPI server for an agent.
    
    Args:
        app: FastAPI application.
        host: Host address to bind the server.
        port: Port to bind the server.
        agent_name: Name of the agent.
    """
    logger.info(f"Starting API server for {agent_name} on {host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")


async def process_command(coordinator: WorkflowCoordinator, command: str) -> Dict[str, Any]:
    """Process a natural language command using Gemini and route to the appropriate agent.
    
    Args:
        coordinator: The workflow coordinator instance.
        command: The natural language command text.
        
    Returns:
        The result of the command processing.
    """
    # Get API key from environment variable or use a default one for demo
    api_key = os.environ.get("GEMINI_API_KEY")
    
    # Determine which agent should handle the command
    agent_type = "manager"  # Default to manager
    agent = coordinator.manager
    agent_name = "ProjectManager"  # Default agent name
    
    # Try to determine the agent type based on command content
    command_lower = command.lower()
    
    if any(cmd in command_lower for cmd in ["create task", "assign task", "list tasks", "review task", "agent status"]):
        agent_type = "manager"
        agent = coordinator.manager
        agent_name = "ProjectManager"
    
    elif any(cmd in command_lower for cmd in ["my tasks", "work on", "complete task", "engineer status"]):
        agent_type = "engineer"
        # Default to first engineer for now
        agent = coordinator.engineers[0] if coordinator.engineers else None
        agent_name = "Engineer1"
    
    elif any(cmd in command_lower for cmd in ["completed tasks", "test task", "submit test", "tester status"]):
        agent_type = "tester"
        # Default to first tester for now
        agent = coordinator.testers[0] if coordinator.testers else None
        agent_name = "Tester1"
    
    logger.info(f"Routing command to {agent_name} ({agent_type})")
    
    if not agent:
        return {"error": f"No {agent_type} agent available"}
    
    # Create NLP handler for the agent
    nlp_handler = AgentNLPHandler(agent_type, api_key)
    
    # Process the command
    result = await nlp_handler.process_command(agent, command)
    
    return {
        "agent": agent_name,
        "result": result
    }


def run_system() -> None:
    """Run the multi-agent project management system."""
    # Check for .env file and Gemini API key
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        env_path = Path('.') / '.env'
        template_path = Path('.') / '.env-template'
        
        if not env_path.exists() and template_path.exists():
            logger.warning("No .env file found. Please copy .env-template to .env and configure it:")
            logger.warning("cp .env-template .env")
            logger.warning("Then edit .env to add your Gemini API key.")
        else:
            logger.warning("GEMINI_API_KEY not found in environment variables or .env file.")
            logger.warning("Natural language features will use fallback mode (limited functionality).")
    
    # Set up the system
    coordinator = setup_system()
    
    # Get the root agent
    root_agent = coordinator.get_root_agent()
    
    # Start the API servers for each agent in separate threads
    api_threads = []
    
    # Manager API
    if hasattr(coordinator.manager, 'app'):
        manager_thread = threading.Thread(
            target=run_api_server,
            args=(coordinator.manager.app, "127.0.0.1", 8001, "ProjectManager"),
            daemon=True
        )
        api_threads.append(manager_thread)
        manager_thread.start()
    
    # Engineer APIs
    for i, engineer in enumerate(coordinator.engineers):
        if hasattr(engineer, 'app'):
            engineer_thread = threading.Thread(
                target=run_api_server,
                args=(engineer.app, "127.0.0.1", 8010 + i, f"Engineer{i+1}"),
                daemon=True
            )
            api_threads.append(engineer_thread)
            engineer_thread.start()
    
    # Tester APIs
    for i, tester in enumerate(coordinator.testers):
        if hasattr(tester, 'app'):
            tester_thread = threading.Thread(
                target=run_api_server,
                args=(tester.app, "127.0.0.1", 8020 + i, f"Tester{i+1}"),
                daemon=True
            )
            api_threads.append(tester_thread)
            tester_thread.start()
    
    # Start the workload rebalancing in a separate thread
    def run_rebalance_task():
        asyncio.run(rebalance_periodically(coordinator))
    
    rebalance_thread = threading.Thread(target=run_rebalance_task, daemon=True)
    rebalance_thread.start()
    
    # Simple message loop for agent interaction
    logger.info("Starting agent system with Gemini natural language processing...")
    
    try:
        while True:
            user_input = input("\nEnter command (or 'exit' to quit): ")
            if user_input.lower() == 'exit':
                break
                
            # Process the command
            print(f"\nProcessing: '{user_input}'...")
            result = asyncio.run(process_command(coordinator, user_input))
            
            # Print the result
            agent_name = result.get("agent", "System")
            if "error" in result:
                print(f"\n{agent_name}: Error - {result['error']}")
            else:
                print(f"\n{agent_name}: {result.get('result', 'Command processed')}")
    except KeyboardInterrupt:
        logger.info("Agent system interrupted. Shutting down...")
    finally:
        logger.info("Agent system shut down. API servers still running in background.")


def cli_loop(coordinator: WorkflowCoordinator):
    """Run a command-line interface loop for interacting with the system.
    
    Args:
        coordinator: The workflow coordinator instance.
    """
    print("Multi-Agent Project Management CLI. Type 'exit' to quit.")
    while True:
        command = input(">>> ")
        if command.strip().lower() in {"exit", "quit"}:
            break
        # Process the command
        print(f"\nProcessing: '{command}'...")
        try:
            result = asyncio.run(process_command(coordinator, command))
            
            # Print the result
            agent_name = result.get("agent", "System")
            if "error" in result:
                print(f"\n{agent_name}: Error - {result['error']}")
            else:
                print(f"\n{agent_name}: {result.get('result', 'Command processed')}")
        except Exception as e:
            print(f"\nError processing command: {str(e)}")


if __name__ == "__main__":
    # Run the system
    run_system()
    # The CLI loop is already in run_system(), so we don't need to call it again 