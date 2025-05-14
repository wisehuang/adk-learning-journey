"""Workflow coordinator for the multi-agent project management system.

This module defines the WorkflowAgent that coordinates the manager, engineer, and tester agents
to work together effectively and balance the workload between them.
"""

import os
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator

from google.adk.agents import BaseAgent, SequentialAgent
from google.adk.events import Event, EventActions
from google.adk.agents.invocation_context import InvocationContext

# Use relative imports
from ..common import Task, TaskStatus, AgentLoad
from ..agents.manager.agent import ManagerAgent
from ..agents.engineer.agent import EngineerAgent
from ..agents.tester.agent import TesterAgent


class WorkflowCoordinator:
    """Coordinator for the multi-agent workflow.
    
    This class sets up and configures the agent hierarchy and shared state for 
    the project management system.
    """
    
    def __init__(self):
        """Initialize the workflow coordinator."""
        # Shared state among agents
        self.tasks_store: Dict[str, Task] = {}
        self.agent_loads: Dict[str, AgentLoad] = {}
        
        # Load capacity settings from environment variables
        manager_capacity = int(os.environ.get("MANAGER_MAX_CAPACITY", 10))
        engineer_capacity = int(os.environ.get("ENGINEER_MAX_CAPACITY", 5))
        tester_capacity = int(os.environ.get("TESTER_MAX_CAPACITY", 3))
        
        # Configure manager agent
        self.manager = ManagerAgent(
            name="ProjectManager",
            tasks_store=self.tasks_store,
            agent_loads=self.agent_loads
        )
        
        # Configure engineer agents
        self.engineers = [
            EngineerAgent(name=f"Engineer{i}", tasks_store=self.tasks_store, agent_loads=self.agent_loads)
            for i in range(1, 4)  # Create 3 engineers
        ]
        
        # Configure tester agents
        self.testers = [
            TesterAgent(name=f"Tester{i}", tasks_store=self.tasks_store, agent_loads=self.agent_loads)
            for i in range(1, 3)  # Create 2 testers
        ]
        
        # Set up agent loads with initial capacities from environment variables
        self.agent_loads["ProjectManager"] = AgentLoad(
            agent_id="ProjectManager",
            agent_type="manager",
            current_tasks=0,
            max_capacity=manager_capacity
        )
        
        for i in range(1, 4):
            self.agent_loads[f"Engineer{i}"] = AgentLoad(
                agent_id=f"Engineer{i}",
                agent_type="engineer",
                current_tasks=0,
                max_capacity=engineer_capacity
            )
            
        for i in range(1, 3):
            self.agent_loads[f"Tester{i}"] = AgentLoad(
                agent_id=f"Tester{i}",
                agent_type="tester",
                current_tasks=0,
                max_capacity=tester_capacity
            )
        
        # Create sequential workflow agent to manage conversation flow
        self.workflow_agent = self._create_workflow_agent()
    
    def _create_workflow_agent(self) -> SequentialAgent:
        """Create the workflow agent that orchestrates interaction between agents.
        
        Returns:
            A SequentialAgent that orchestrates the workflow.
        """
        # Set up the routing agent
        workflow_agent = SequentialAgent(
            name="ProjectManagementSystem",
            description="A project management system with manager, engineer, and tester agents",
            # The order here doesn't impact the agent delegation,
            # which is handled by the Router agent
            sub_agents=[
                self.manager,
                *self.engineers,
                *self.testers
            ]
        )
        
        return workflow_agent
    
    def get_root_agent(self) -> BaseAgent:
        """Get the root agent for the system.
        
        Returns:
            The root agent that handles the conversation flow.
        """
        return self.workflow_agent
    
    def get_agent_by_name(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by its name.
        
        Args:
            name: The name of the agent to retrieve.
            
        Returns:
            The agent with the specified name, or None if not found.
        """
        if name == "ProjectManager":
            return self.manager
            
        for engineer in self.engineers:
            if engineer.name == name:
                return engineer
                
        for tester in self.testers:
            if tester.name == name:
                return tester
                
        return None
    
    def get_all_agents(self) -> List[BaseAgent]:
        """Get all agents in the system.
        
        Returns:
            A list of all agents in the system.
        """
        return [self.manager, *self.engineers, *self.testers]
    
    def rebalance_workload(self) -> Dict[str, AgentLoad]:
        """Rebalance workload among agents based on current state.
        
        This method checks the current agent loads and tasks, and redistributes 
        tasks as needed to balance the workload.
        
        Returns:
            Updated agent load information.
        """
        # Count current tasks for each agent
        for agent_id in self.agent_loads:
            self.agent_loads[agent_id].current_tasks = 0
            
        # Update task counts based on task assignments
        for task_id, task in self.tasks_store.items():
            if task.assigned_to and task.assigned_to in self.agent_loads:
                self.agent_loads[task.assigned_to].current_tasks += 1
        
        # Find engineers with high load
        overloaded_engineers = []
        for agent_id, load in self.agent_loads.items():
            if load.agent_type == "engineer" and load.load_percentage > 80:
                overloaded_engineers.append((agent_id, load))
        
        # Find engineers with low load
        underloaded_engineers = []
        for agent_id, load in self.agent_loads.items():
            if load.agent_type == "engineer" and load.load_percentage < 50:
                underloaded_engineers.append((agent_id, load))
                
        # Rebalance tasks from overloaded to underloaded engineers if possible
        for over_id, over_load in overloaded_engineers:
            for under_id, under_load in underloaded_engineers:
                # Find tasks that can be reassigned
                for task_id, task in self.tasks_store.items():
                    if (task.assigned_to == over_id and 
                        task.status == TaskStatus.IN_PROGRESS and
                        not task.dependencies):  # Only reassign independent tasks
                        
                        # Reassign the task
                        task.assigned_to = under_id
                        task.comments.append(f"[{datetime.now()}] Task reassigned from {over_id} to {under_id} for load balancing.")
                        
                        # Update agent loads
                        self.agent_loads[over_id].current_tasks -= 1
                        self.agent_loads[under_id].current_tasks += 1
                        break
                        
                # Check if we've sufficiently reduced the load
                if self.agent_loads[over_id].load_percentage <= 80:
                    break
        
        return self.agent_loads 