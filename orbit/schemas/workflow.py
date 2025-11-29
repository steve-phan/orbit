from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel
from orbit.models.workflow import TaskBase, WorkflowBase


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: UUID
    workflow_id: UUID
    status: str
    retry_count: int


class WorkflowCreate(WorkflowBase):
    tasks: List[TaskCreate]


class WorkflowRead(WorkflowBase):
    id: UUID
    status: str
    tasks: List[TaskRead]
