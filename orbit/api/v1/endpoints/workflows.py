from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.dependencies import (
    get_task_repository,
    get_workflow_repository,
    get_workflow_service,
)
from orbit.core.exceptions import (
    DAGValidationError,
    OrbitException,
    WorkflowNotFoundError,
)
from orbit.core.logging import get_logger
from orbit.db.session import get_session
from orbit.repositories.workflow_repository import TaskRepository, WorkflowRepository
from orbit.schemas.workflow import WorkflowCreate, WorkflowRead
from orbit.services.task_runner import TaskRunner
from orbit.services.websocket_manager import ws_manager

logger = get_logger("api.workflows")
router = APIRouter()


@router.post("/", response_model=WorkflowRead, status_code=201)
async def create_workflow(
    workflow_in: WorkflowCreate,
    session: AsyncSession = Depends(get_session),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    task_repo: TaskRepository = Depends(get_task_repository),
):
    """
    Create a new workflow with tasks.
    Validates DAG structure before creation.
    """
    try:
        service = get_workflow_service(workflow_repo, task_repo)
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
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    task_repo: TaskRepository = Depends(get_task_repository),
):
    """List all workflows with pagination."""
    try:
        service = get_workflow_service(workflow_repo, task_repo)
        workflows = await service.list_workflows(skip=skip, limit=limit)
        return workflows
    except OrbitException as e:
        logger.error(f"Failed to list workflows: {e.message}")
        raise HTTPException(status_code=500, detail=e.message)


@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    task_repo: TaskRepository = Depends(get_task_repository),
):
    """Get a specific workflow by ID."""
    try:
        service = get_workflow_service(workflow_repo, task_repo)
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
    workflow_repo: WorkflowRepository = Depends(get_workflow_repository),
    task_repo: TaskRepository = Depends(get_task_repository),
):
    """Execute a workflow in the background."""
    try:
        service = get_workflow_service(workflow_repo, task_repo)
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
