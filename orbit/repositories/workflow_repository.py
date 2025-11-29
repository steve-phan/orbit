"""
Repository pattern for Workflow data access.
Abstracts database operations for better testability and maintainability.
"""

from uuid import UUID

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.exceptions import DatabaseError, WorkflowNotFoundError
from orbit.core.logging import get_logger
from orbit.models.workflow import Task, Workflow

logger = get_logger("repositories.workflow")


class WorkflowRepository:
    """Repository for Workflow entity operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, workflow: Workflow) -> Workflow:
        """Create a new workflow."""
        try:
            self.session.add(workflow)
            await self.session.commit()
            await self.session.refresh(workflow)
            logger.info(f"Created workflow: {workflow.id}")
            return workflow
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create workflow: {e}")
            raise DatabaseError(f"Failed to create workflow: {str(e)}")

    async def get_by_id(
        self, workflow_id: UUID, include_tasks: bool = True
    ) -> Workflow:
        """Get workflow by ID."""
        try:
            query = select(Workflow).where(Workflow.id == workflow_id)
            if include_tasks:
                query = query.options(selectinload(Workflow.tasks))

            result = await self.session.exec(query)
            workflow = result.first()

            if not workflow:
                raise WorkflowNotFoundError(
                    f"Workflow {workflow_id} not found",
                    details={"workflow_id": str(workflow_id)},
                )

            return workflow
        except WorkflowNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get workflow {workflow_id}: {e}")
            raise DatabaseError(f"Failed to get workflow: {str(e)}")

    async def get_all(
        self, skip: int = 0, limit: int = 100, include_tasks: bool = True
    ) -> list[Workflow]:
        """Get all workflows with pagination."""
        try:
            query = select(Workflow).offset(skip).limit(limit)
            if include_tasks:
                query = query.options(selectinload(Workflow.tasks))

            result = await self.session.exec(query)
            workflows = result.all()
            logger.debug(f"Retrieved {len(workflows)} workflows")
            return list(workflows)
        except Exception as e:
            logger.error(f"Failed to get workflows: {e}")
            raise DatabaseError(f"Failed to get workflows: {str(e)}")

    async def update(self, workflow: Workflow) -> Workflow:
        """Update an existing workflow."""
        try:
            self.session.add(workflow)
            await self.session.commit()
            await self.session.refresh(workflow)
            logger.info(f"Updated workflow: {workflow.id}")
            return workflow
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update workflow {workflow.id}: {e}")
            raise DatabaseError(f"Failed to update workflow: {str(e)}")

    async def delete(self, workflow_id: UUID) -> None:
        """Delete a workflow."""
        try:
            workflow = await self.get_by_id(workflow_id, include_tasks=False)
            await self.session.delete(workflow)
            await self.session.commit()
            logger.info(f"Deleted workflow: {workflow_id}")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to delete workflow {workflow_id}: {e}")
            raise DatabaseError(f"Failed to delete workflow: {str(e)}")


class TaskRepository:
    """Repository for Task entity operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, task: Task) -> Task:
        """Create a new task."""
        try:
            self.session.add(task)
            await self.session.commit()
            await self.session.refresh(task)
            logger.info(f"Created task: {task.id}")
            return task
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create task: {e}")
            raise DatabaseError(f"Failed to create task: {str(e)}")

    async def create_many(self, tasks: list[Task]) -> list[Task]:
        """Create multiple tasks."""
        try:
            for task in tasks:
                self.session.add(task)
            await self.session.commit()

            for task in tasks:
                await self.session.refresh(task)

            logger.info(f"Created {len(tasks)} tasks")
            return tasks
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create tasks: {e}")
            raise DatabaseError(f"Failed to create tasks: {str(e)}")

    async def update(self, task: Task) -> Task:
        """Update an existing task."""
        try:
            self.session.add(task)
            await self.session.commit()
            await self.session.refresh(task)
            logger.debug(f"Updated task: {task.id}")
            return task
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update task {task.id}: {e}")
            raise DatabaseError(f"Failed to update task: {str(e)}")
