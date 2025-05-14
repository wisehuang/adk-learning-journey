"""Common data models and utilities for the multi-agent project management system."""

from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Status of a task in the system."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    TESTING = "testing"
    APPROVED = "approved"
    REJECTED = "rejected"


class TaskPriority(str, Enum):
    """Priority level for tasks."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TaskType(str, Enum):
    """Type of task to be performed."""
    FEATURE = "feature"
    BUG = "bug"
    IMPROVEMENT = "improvement"
    DOCUMENTATION = "documentation"


class Task(BaseModel):
    """Represents a project management task."""
    id: str
    title: str
    description: str
    status: TaskStatus = TaskStatus.PENDING
    priority: TaskPriority = TaskPriority.MEDIUM
    task_type: TaskType
    assigned_to: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    dependencies: List[str] = Field(default_factory=list)
    comments: List[str] = Field(default_factory=list)
    test_results: Optional[Dict[str, str]] = None


class AgentLoad(BaseModel):
    """Represents the current workload of an agent."""
    agent_id: str
    agent_type: str  # "manager", "engineer", "tester"
    current_tasks: int
    max_capacity: int
    
    @property
    def load_percentage(self) -> float:
        """Calculate the load percentage.
        
        Returns:
            The percentage of capacity currently in use (0-100).
        """
        if self.max_capacity == 0:
            return 0.0
        return (self.current_tasks / self.max_capacity) * 100.0
    
    @property
    def available_capacity(self) -> int:
        """Calculate the available capacity.
        
        Returns:
            The number of additional tasks that can be assigned.
        """
        return max(0, self.max_capacity - self.current_tasks)


class TaskAssignment(BaseModel):
    """Represents a task assignment request."""
    task_id: str
    agent_id: str


class TaskStatusUpdate(BaseModel):
    """Represents a task status update."""
    task_id: str
    new_status: TaskStatus
    message: Optional[str] = None
    test_results: Optional[Dict[str, str]] = None


def get_timestamp() -> str:
    """Get a formatted timestamp string.
    
    Returns:
        A string representation of the current time.
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S") 