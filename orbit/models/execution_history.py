"""
Execution history model.
Tracks all workflow and task executions for audit and debugging.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel
from sqlalchemy import Column, JSON, Text


class WorkflowExecution(SQLModel, table=True):
    """
    Records each workflow execution attempt.
    Provides audit trail and execution history.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    workflow_name: str = Field(index=True)
    status: str = Field(index=True)  # queued, running, completed, failed, cancelled
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON))


class TaskExecution(SQLModel, table=True):
    """
    Records each task execution attempt.
    Tracks retries and execution details.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_execution_id: UUID = Field(
        foreign_key="workflowexecution.id", index=True
    )
    task_id: UUID = Field(foreign_key="task.id", index=True)
    task_name: str = Field(index=True)
    attempt_number: int = Field(default=0)  # Retry attempt
    status: str = Field(index=True)  # pending, running, completed, failed
    started_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: Optional[datetime] = Field(default=None)
    duration_seconds: Optional[float] = Field(default=None)
    error_message: Optional[str] = Field(default=None, sa_column=Column(Text))
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
