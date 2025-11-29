from datetime import datetime
from typing import List, Optional
from uuid import UUID, uuid4
from sqlmodel import Field, Relationship, SQLModel
from sqlalchemy import Column, String, JSON

class WorkflowBase(SQLModel):
    name: str = Field(index=True)
    description: Optional[str] = None

class Workflow(WorkflowBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    status: str = Field(default="pending", index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    tasks: List["Task"] = Relationship(back_populates="workflow")

class TaskBase(SQLModel):
    name: str
    action_type: str  # e.g., "http_request", "shell_command"
    action_payload: dict = Field(default_factory=dict, sa_column=Column(JSON))
    dependencies: List[str] = Field(default_factory=list, sa_column=Column(JSON)) # List of task names this task depends on

class Task(TaskBase, table=True):
    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id")
    status: str = Field(default="pending")
    result: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    workflow: Workflow = Relationship(back_populates="tasks")
