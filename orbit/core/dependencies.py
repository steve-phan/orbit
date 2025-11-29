"""
Dependency injection container.
Provides centralized dependency management.
"""

from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.repositories.workflow_repository import TaskRepository, WorkflowRepository
from orbit.services.workflow_service import WorkflowService


def get_workflow_repository(session: AsyncSession) -> WorkflowRepository:
    """Get workflow repository instance."""
    return WorkflowRepository(session)


def get_task_repository(session: AsyncSession) -> TaskRepository:
    """Get task repository instance."""
    return TaskRepository(session)


def get_workflow_service(
    workflow_repo: WorkflowRepository, task_repo: TaskRepository
) -> WorkflowService:
    """Get workflow service instance."""
    return WorkflowService(workflow_repo, task_repo)
