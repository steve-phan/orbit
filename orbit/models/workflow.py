from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column
from sqlmodel import Field, Relationship, SQLModel


class WorkflowBase(SQLModel):
    name: str = Field(index=True)
    description: str | None = None


class Workflow(WorkflowBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    paused_at: datetime | None = Field(
        default=None, description="Timestamp when workflow was paused"
    )

    tasks: list["Task"] = Relationship(back_populates="workflow")


class TaskBase(SQLModel):
    name: str
    action_type: str  # e.g., "http_request", "shell_command"
    action_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    dependencies: list[str] = Field(
        default_factory=list, sa_column=Column(JSON)
    )  # List of task names this task depends on
    retry_policy: dict | None = Field(
        default=None, sa_column=Column(JSON)
    )  # Retry configuration
    timeout_seconds: int | None = Field(
        default=None
    )  # Task timeout in seconds


class Task(TaskBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id")
    status: str = Field(default="pending")
    result: dict | None = Field(default=None, sa_column=Column(JSON))
    retry_count: int = Field(default=0)  # Current retry attempt
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    workflow: Workflow = Relationship(back_populates="tasks")
