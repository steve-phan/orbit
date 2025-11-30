"""
Workflow scheduler service.
Manages periodic workflow execution based on cron schedules.
"""

import asyncio
from datetime import datetime

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.logging import get_logger
from orbit.models.schedule import WorkflowSchedule
from orbit.models.workflow import Workflow

logger = get_logger("services.scheduler")


class WorkflowScheduler:
    """
    Manages workflow scheduling and execution.
    Runs as a background task checking for due workflows.
    """

    def __init__(self, check_interval: int = 60):
        """
        Initialize scheduler.

        Args:
            check_interval: Interval in seconds to check for due workflows
        """
        self.check_interval = check_interval
        self.running = False
        self._task: asyncio.Task | None = None

    async def start(self, session_factory) -> None:
        """
        Start the scheduler background task.

        Args:
            session_factory: Factory function to create database sessions
        """
        if self.running:
            logger.warning("Scheduler already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._run_scheduler(session_factory))
        logger.info(
            f"Workflow scheduler started (check interval: {self.check_interval}s)"
        )

    async def stop(self) -> None:
        """Stop the scheduler background task."""
        if not self.running:
            return

        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Workflow scheduler stopped")

    async def _run_scheduler(self, session_factory) -> None:
        """
        Main scheduler loop.
        Checks for due workflows and triggers execution.
        """
        while self.running:
            try:
                async with session_factory() as session:
                    await self._check_and_execute_due_workflows(session)
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}", exc_info=True)

            # Wait before next check
            await asyncio.sleep(self.check_interval)

    async def _check_and_execute_due_workflows(
        self, session: AsyncSession
    ) -> None:
        """
        Check for workflows that are due to run and execute them.

        Args:
            session: Database session
        """
        now = datetime.utcnow()

        # Find all enabled schedules that are due
        statement = (
            select(WorkflowSchedule)
            .where(WorkflowSchedule.enabled == True)  # noqa: E712
            .where(
                (WorkflowSchedule.next_run <= now) | (WorkflowSchedule.next_run.is_(None))
            )
        )

        result = await session.exec(statement)
        due_schedules = result.all()

        logger.debug(f"Found {len(due_schedules)} due workflows")

        for schedule in due_schedules:
            try:
                await self._execute_scheduled_workflow(session, schedule)
            except Exception as e:
                logger.error(
                    f"Failed to execute scheduled workflow {schedule.workflow_id}: {e}",
                    exc_info=True,
                )

    async def _execute_scheduled_workflow(
        self, session: AsyncSession, schedule: WorkflowSchedule
    ) -> None:
        """
        Execute a scheduled workflow.

        Args:
            session: Database session
            schedule: Workflow schedule
        """
        # Verify workflow exists
        workflow_statement = select(Workflow).where(
            Workflow.id == schedule.workflow_id
        )
        workflow_result = await session.exec(workflow_statement)
        workflow = workflow_result.first()

        if not workflow:
            logger.error(f"Workflow {schedule.workflow_id} not found, disabling schedule")
            schedule.enabled = False
            session.add(schedule)
            await session.commit()
            return

        # Check if workflow is already running
        if workflow.status == "running":
            logger.warning(
                f"Workflow {workflow.id} is already running, skipping scheduled execution"
            )
            # Still update next_run to prevent repeated attempts
            schedule.last_run = datetime.utcnow()
            schedule.update_next_run()
            session.add(schedule)
            await session.commit()
            return

        logger.info(f"Executing scheduled workflow: {workflow.name} ({workflow.id})")

        # Trigger workflow execution (this will be handled by existing execution logic)
        from orbit.api.v1.endpoints.workflows import execute_workflow_task

        # Update schedule
        schedule.last_run = datetime.utcnow()
        schedule.update_next_run()
        session.add(schedule)
        await session.commit()

        # Execute workflow in background
        asyncio.create_task(execute_workflow_task(workflow.id))

        logger.info(
            f"Scheduled workflow {workflow.name} triggered. Next run: {schedule.next_run}"
        )


# Global scheduler instance
scheduler = WorkflowScheduler(check_interval=60)
