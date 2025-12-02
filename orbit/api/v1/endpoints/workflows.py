from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.exceptions import (
    DAGValidationError,
    OrbitException,
    WorkflowNotFoundError,
)
from orbit.core.logging import get_logger
from orbit.db.session import get_session
from orbit.repositories.workflow_repository import TaskRepository, WorkflowRepository
from orbit.schemas.workflow import WorkflowCreate, WorkflowRead
from orbit.services.pause_resume import WorkflowControlService
from orbit.services.task_runner import TaskRunner
from orbit.services.websocket_manager import ws_manager

logger = get_logger("api.workflows")
router = APIRouter()


@router.post("/", response_model=WorkflowRead, status_code=201)
async def create_workflow(
    workflow_in: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new workflow with tasks.
    Validates DAG structure before creation.
    """
    try:
        workflow_repo = WorkflowRepository(session)
        task_repo = TaskRepository(session)
        from orbit.services.workflow_service import WorkflowService
        service = WorkflowService(workflow_repo, task_repo)
        workflow = await service.create_workflow(workflow_in)
        return workflow
    except DAGValidationError as e:
        logger.warning(f"DAG validation failed: {e.message}")
        raise HTTPException(status_code=400, detail=e.message)
    except OrbitException as e:
        logger.error(f"Failed to create workflow: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/", response_model=list[WorkflowRead])
async def read_workflows(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    """List all workflows with pagination."""
    try:
        workflow_repo = WorkflowRepository(session)
        task_repo = TaskRepository(session)
        from orbit.services.workflow_service import WorkflowService
        service = WorkflowService(workflow_repo, task_repo)
        workflows = await service.list_workflows(skip=skip, limit=limit)
        return workflows
    except OrbitException as e:
        logger.error(f"Failed to list workflows: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific workflow by ID."""
    try:
        workflow_repo = WorkflowRepository(session)
        task_repo = TaskRepository(session)
        from orbit.services.workflow_service import WorkflowService
        service = WorkflowService(workflow_repo, task_repo)
        workflow = await service.get_workflow(workflow_id)
        return workflow
    except WorkflowNotFoundError as e:
        logger.warning(f"Workflow not found: {workflow_id}")
        raise HTTPException(status_code=404, detail=e.message)
    except OrbitException as e:
        logger.error(f"Failed to get workflow: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """Execute a workflow in the background."""
    try:
        workflow_repo = WorkflowRepository(session)
        task_repo = TaskRepository(session)
        from orbit.services.workflow_service import WorkflowService
        service = WorkflowService(workflow_repo, task_repo)
        workflow = await service.get_workflow(workflow_id)

        if workflow.status == "running":
            raise HTTPException(status_code=400, detail="Workflow is already running")

        # Execute workflow in background
        background_tasks.add_task(execute_workflow_task, workflow_id)

        logger.info(f"Queued workflow {workflow_id} for execution")

        return {
            "workflow_id": str(workflow_id),
            "status": "queued",
            "message": "Workflow execution started",
        }
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except OrbitException as e:
        logger.error(f"Failed to execute workflow: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


async def execute_workflow_task(workflow_id: UUID):
    """Background task to execute workflow."""
    from sqlalchemy.orm import sessionmaker
    from sqlmodel.ext.asyncio.session import AsyncSession

    from orbit.db.session import engine

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        runner = TaskRunner(session, ws_manager)
        try:
            await runner.execute_workflow(workflow_id)
        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")


@router.post("/{workflow_id}/pause")
async def pause_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Pause a running or pending workflow.
    Paused workflows can be resumed later.
    """
    try:
        control_service = WorkflowControlService(session)
        workflow = await control_service.pause_workflow(workflow_id)

        # Broadcast pause event
        await ws_manager.broadcast(
            {
                "workflow_id": str(workflow_id),
                "status": "paused",
                "paused_at": workflow.paused_at.isoformat() if workflow.paused_at else None,
            }
        )

        return {
            "workflow_id": str(workflow_id),
            "status": "paused",
            "message": "Workflow paused successfully",
        }
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrbitException as e:
        logger.error(f"Failed to pause workflow: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/{workflow_id}/resume")
async def resume_workflow(
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Resume a paused workflow.
    The workflow will continue execution from where it was paused.
    """
    try:
        control_service = WorkflowControlService(session)
        await control_service.resume_workflow(workflow_id)

        # Broadcast resume event
        await ws_manager.broadcast(
            {"workflow_id": str(workflow_id), "status": "resumed"}
        )

        # Re-queue workflow for execution
        background_tasks.add_task(execute_workflow_task, workflow_id)

        return {
            "workflow_id": str(workflow_id),
            "status": "resumed",
            "message": "Workflow resumed successfully",
        }
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrbitException as e:
        logger.error(f"Failed to resume workflow: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.post("/{workflow_id}/cancel")
async def cancel_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Cancel a workflow permanently.
    Cancelled workflows cannot be resumed.
    """
    try:
        control_service = WorkflowControlService(session)
        await control_service.cancel_workflow(workflow_id)

        # Broadcast cancel event
        await ws_manager.broadcast(
            {"workflow_id": str(workflow_id), "status": "cancelled"}
        )

        return {
            "workflow_id": str(workflow_id),
            "status": "cancelled",
            "message": "Workflow cancelled successfully",
        }
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except OrbitException as e:
        logger.error(f"Failed to cancel workflow: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/{workflow_id}/status")
async def get_workflow_status(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """
    Get detailed status of a workflow including pause/resume capabilities.
    """
    try:
        control_service = WorkflowControlService(session)
        status = await control_service.get_workflow_status(workflow_id)
        return status
    except WorkflowNotFoundError as e:
        raise HTTPException(status_code=404, detail=e.message)
    except OrbitException as e:
        logger.error(f"Failed to get workflow status: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)
