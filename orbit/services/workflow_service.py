"""
Workflow service layer.
Handles business logic for workflow operations.
"""

from datetime import datetime
from uuid import UUID

from orbit.core.exceptions import DAGValidationError
from orbit.core.logging import get_logger
from orbit.models.workflow import Task, Workflow
from orbit.repositories.workflow_repository import TaskRepository, WorkflowRepository
from orbit.schemas.workflow import WorkflowCreate
from orbit.services.dag_executor import DAGExecutor

logger = get_logger("services.workflow")


class WorkflowService:
    """Service for workflow business logic."""

    def __init__(self, workflow_repo: WorkflowRepository, task_repo: TaskRepository):
        self.workflow_repo = workflow_repo
        self.task_repo = task_repo

    async def create_workflow(self, workflow_data: WorkflowCreate) -> Workflow:
        """
        Create a new workflow with tasks.
        Validates DAG structure before creation.
        """
        logger.info(f"Creating workflow: {workflow_data.name}")

        # Create workflow entity
        workflow = Workflow(
            name=workflow_data.name, description=workflow_data.description
        )
        workflow = await self.workflow_repo.create(workflow)

        # Create task entities
        tasks = []
        for task_data in workflow_data.tasks:
            task = Task(
                workflow_id=workflow.id,
                name=task_data.name,
                action_type=task_data.action_type,
                action_payload=task_data.action_payload,
                dependencies=task_data.dependencies,
            )
            tasks.append(task)

        # Validate DAG structure
        try:
            DAGExecutor.validate_dag(tasks)
        except ValueError as e:
            logger.error(f"DAG validation failed: {e}")
            # Rollback workflow creation
            await self.workflow_repo.delete(workflow.id)
            raise DAGValidationError(str(e), details={"workflow_id": str(workflow.id)})

        # Create tasks
        tasks = await self.task_repo.create_many(tasks)

        # Reload workflow with tasks
        workflow = await self.workflow_repo.get_by_id(workflow.id)

        logger.info(
            f"Successfully created workflow {workflow.id} with {len(tasks)} tasks"
        )
        return workflow

    async def get_workflow(self, workflow_id: UUID) -> Workflow:
        """Get workflow by ID."""
        logger.debug(f"Retrieving workflow: {workflow_id}")
        return await self.workflow_repo.get_by_id(workflow_id)

    async def list_workflows(self, skip: int = 0, limit: int = 100) -> list[Workflow]:
        """List all workflows with pagination."""
        logger.debug(f"Listing workflows (skip={skip}, limit={limit})")
        return await self.workflow_repo.get_all(skip=skip, limit=limit)

    async def update_workflow_status(self, workflow_id: UUID, status: str) -> Workflow:
        """Update workflow status."""
        logger.info(f"Updating workflow {workflow_id} status to {status}")

        workflow = await self.workflow_repo.get_by_id(workflow_id, include_tasks=False)
        workflow.status = status
        workflow.updated_at = datetime.utcnow()

        return await self.workflow_repo.update(workflow)

    async def delete_workflow(self, workflow_id: UUID) -> None:
        """Delete a workflow."""
        logger.info(f"Deleting workflow: {workflow_id}")
        await self.workflow_repo.delete(workflow_id)
