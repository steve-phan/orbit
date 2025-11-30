"""
Dynamic task generation models.
Enables map-reduce patterns for parallel processing of arrays.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class DynamicTaskGroup(SQLModel, table=True):
    """
    Represents a group of dynamically generated tasks.
    Used for map-reduce patterns.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    parent_task_name: str = Field(index=True, description="Name of the map/reduce task")

    # Task generation
    task_type: str = Field(description="Type: map or reduce")
    items: list[Any] = Field(sa_column=Column(JSON), description="Items to process")
    task_template: dict[str, Any] = Field(sa_column=Column(JSON), description="Template for generated tasks")

    # Status
    total_tasks: int = Field(default=0)
    completed_tasks: int = Field(default=0)
    failed_tasks: int = Field(default=0)
    status: str = Field(default="pending", index=True)  # pending, running, completed, failed

    # Results
    results: list[Any] | None = Field(default=None, sa_column=Column(JSON))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = Field(default=None)

    def progress_percentage(self) -> float:
        """Calculate completion percentage."""
        if self.total_tasks == 0:
            return 0.0
        return (self.completed_tasks / self.total_tasks) * 100
