"""
Workflow pause/resume service.
Provides manual control over workflow execution.
"""

from datetime import datetime
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.exceptions import WorkflowNotFoundError
from orbit.core.logging import get_logger
from orbit.models.workflow import Workflow

logger = get_logger("services.pause_resume")


class WorkflowControlService:
    """
    Service for pausing and resuming workflows.
    Provides manual control over workflow execution.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def pause_workflow(self, workflow_id: UUID) -> Workflow:
        """
        Pause a running workflow.

        Args:
            workflow_id: UUID of the workflow to pause

        Returns:
            Updated workflow

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            ValueError: If workflow is not in a pausable state
        """
        # Get workflow
        statement = select(Workflow).where(Workflow.id == workflow_id)
        result = await self.session.exec(statement)
        workflow = result.first()

        if not workflow:
            raise WorkflowNotFoundError(
                f"Workflow {workflow_id} not found",
                details={"workflow_id": str(workflow_id)},
            )

        # Check if workflow can be paused
        if workflow.status not in ["running", "pending"]:
            raise ValueError(
                f"Cannot pause workflow in '{workflow.status}' state. "
                "Only 'running' or 'pending' workflows can be paused."
            )

        if workflow.paused_at is not None:
            logger.warning(f"Workflow {workflow_id} is already paused")
            return workflow

        # Pause workflow
        workflow.status = "paused"
        workflow.paused_at = datetime.utcnow()
        workflow.updated_at = datetime.utcnow()

        self.session.add(workflow)
        await self.session.commit()
        await self.session.refresh(workflow)

        logger.info(f"Paused workflow {workflow_id}")

        return workflow

    async def resume_workflow(self, workflow_id: UUID) -> Workflow:
        """
        Resume a paused workflow.

        Args:
            workflow_id: UUID of the workflow to resume

        Returns:
            Updated workflow

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            ValueError: If workflow is not paused
        """
        # Get workflow
        statement = select(Workflow).where(Workflow.id == workflow_id)
        result = await self.session.exec(statement)
        workflow = result.first()

        if not workflow:
            raise WorkflowNotFoundError(
                f"Workflow {workflow_id} not found",
                details={"workflow_id": str(workflow_id)},
            )

        # Check if workflow is paused
        if workflow.status != "paused":
            raise ValueError(
                f"Cannot resume workflow in '{workflow.status}' state. "
                "Only 'paused' workflows can be resumed."
            )

        # Resume workflow
        # Determine new status based on whether it was running or pending
        if workflow.paused_at:
            # If it was paused, resume to pending (will be picked up by scheduler)
            workflow.status = "pending"
            workflow.paused_at = None
        else:
            workflow.status = "pending"

        workflow.updated_at = datetime.utcnow()

        self.session.add(workflow)
        await self.session.commit()
        await self.session.refresh(workflow)

        logger.info(f"Resumed workflow {workflow_id}")

        return workflow

    async def cancel_workflow(self, workflow_id: UUID) -> Workflow:
        """
        Cancel a workflow (stop execution permanently).

        Args:
            workflow_id: UUID of the workflow to cancel

        Returns:
            Updated workflow

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
            ValueError: If workflow is already completed or failed
        """
        # Get workflow
        statement = select(Workflow).where(Workflow.id == workflow_id)
        result = await self.session.exec(statement)
        workflow = result.first()

        if not workflow:
            raise WorkflowNotFoundError(
                f"Workflow {workflow_id} not found",
                details={"workflow_id": str(workflow_id)},
            )

        # Check if workflow can be cancelled
        if workflow.status in ["completed", "failed", "cancelled"]:
            raise ValueError(
                f"Cannot cancel workflow in '{workflow.status}' state. "
                "Workflow is already in a terminal state."
            )

        # Cancel workflow
        workflow.status = "cancelled"
        workflow.updated_at = datetime.utcnow()

        self.session.add(workflow)
        await self.session.commit()
        await self.session.refresh(workflow)

        logger.info(f"Cancelled workflow {workflow_id}")

        return workflow

    async def get_workflow_status(self, workflow_id: UUID) -> dict:
        """
        Get detailed status of a workflow.

        Args:
            workflow_id: UUID of the workflow

        Returns:
            Dictionary with workflow status details

        Raises:
            WorkflowNotFoundError: If workflow doesn't exist
        """
        statement = select(Workflow).where(Workflow.id == workflow_id)
        result = await self.session.exec(statement)
        workflow = result.first()

        if not workflow:
            raise WorkflowNotFoundError(
                f"Workflow {workflow_id} not found",
                details={"workflow_id": str(workflow_id)},
            )

        return {
            "workflow_id": str(workflow.id),
            "name": workflow.name,
            "status": workflow.status,
            "is_paused": workflow.status == "paused",
            "paused_at": workflow.paused_at.isoformat() if workflow.paused_at else None,
            "created_at": workflow.created_at.isoformat(),
            "updated_at": workflow.updated_at.isoformat(),
            "can_pause": workflow.status in ["running", "pending"],
            "can_resume": workflow.status == "paused",
            "can_cancel": workflow.status
            not in ["completed", "failed", "cancelled"],
        }
