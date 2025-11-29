"""
API endpoints for workflow scheduling.
"""

from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.db.session import get_session
from orbit.models.schedule import WorkflowSchedule
from orbit.models.workflow import Workflow
from orbit.schemas.schedule import ScheduleCreate, ScheduleRead, ScheduleUpdate
from orbit.core.logging import get_logger

logger = get_logger("api.schedules")
router = APIRouter()


@router.post("/{workflow_id}/schedule", response_model=ScheduleRead, status_code=201)
async def create_schedule(
    workflow_id: UUID,
    schedule_in: ScheduleCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a schedule for a workflow.
    """
    # Verify workflow exists
    workflow_statement = select(Workflow).where(Workflow.id == workflow_id)
    workflow_result = await session.exec(workflow_statement)
    workflow = workflow_result.first()

    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Check if schedule already exists
    existing_statement = select(WorkflowSchedule).where(
        WorkflowSchedule.workflow_id == workflow_id
    )
    existing_result = await session.exec(existing_statement)
    existing = existing_result.first()

    if existing:
        raise HTTPException(
            status_code=400, detail="Schedule already exists for this workflow"
        )

    # Create schedule
    schedule = WorkflowSchedule(
        workflow_id=workflow_id,
        cron_expression=schedule_in.cron_expression,
        timezone=schedule_in.timezone,
        enabled=schedule_in.enabled,
    )

    # Calculate initial next_run
    schedule.update_next_run()

    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    logger.info(
        f"Created schedule for workflow {workflow_id}: {schedule.cron_expression}"
    )

    return schedule


@router.get("/{workflow_id}/schedule", response_model=ScheduleRead)
async def get_schedule(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Get the schedule for a workflow.
    """
    statement = select(WorkflowSchedule).where(
        WorkflowSchedule.workflow_id == workflow_id
    )
    result = await session.exec(statement)
    schedule = result.first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    return schedule


@router.put("/{workflow_id}/schedule", response_model=ScheduleRead)
async def update_schedule(
    workflow_id: UUID,
    schedule_update: ScheduleUpdate,
    session: AsyncSession = Depends(get_session),
):
    """
    Update a workflow schedule.
    """
    statement = select(WorkflowSchedule).where(
        WorkflowSchedule.workflow_id == workflow_id
    )
    result = await session.exec(statement)
    schedule = result.first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    # Update fields
    if schedule_update.cron_expression is not None:
        schedule.cron_expression = schedule_update.cron_expression
        schedule.update_next_run()  # Recalculate next run

    if schedule_update.timezone is not None:
        schedule.timezone = schedule_update.timezone

    if schedule_update.enabled is not None:
        schedule.enabled = schedule_update.enabled

    session.add(schedule)
    await session.commit()
    await session.refresh(schedule)

    logger.info(f"Updated schedule for workflow {workflow_id}")

    return schedule


@router.delete("/{workflow_id}/schedule", status_code=204)
async def delete_schedule(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Delete a workflow schedule.
    """
    statement = select(WorkflowSchedule).where(
        WorkflowSchedule.workflow_id == workflow_id
    )
    result = await session.exec(statement)
    schedule = result.first()

    if not schedule:
        raise HTTPException(status_code=404, detail="Schedule not found")

    await session.delete(schedule)
    await session.commit()

    logger.info(f"Deleted schedule for workflow {workflow_id}")

    return None
