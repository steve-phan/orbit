from uuid import UUID

from orbit.models.workflow import TaskBase, WorkflowBase


class TaskCreate(TaskBase):
    pass


class TaskRead(TaskBase):
    id: UUID
    workflow_id: UUID
    status: str
    retry_count: int


class WorkflowCreate(WorkflowBase):
    tasks: list[TaskCreate]


class WorkflowRead(WorkflowBase):
    id: UUID
    status: str
    tasks: list[TaskRead]
