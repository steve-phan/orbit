import asyncio
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlalchemy.orm import selectinload
from typing import List

from orbit.db.session import get_session
from orbit.models.workflow import Workflow, Task
from orbit.schemas.workflow import WorkflowCreate, WorkflowRead, TaskCreate
from orbit.services.dag_executor import DAGExecutor
from orbit.services.task_runner import TaskRunner
from orbit.services.websocket_manager import ws_manager

router = APIRouter()

@router.post("/", response_model=WorkflowRead)
async def create_workflow(
    workflow_in: WorkflowCreate,
    session: AsyncSession = Depends(get_session)
):
    # 1. Create Workflow
    workflow = Workflow(name=workflow_in.name, description=workflow_in.description)
    session.add(workflow)
    await session.commit()
    await session.refresh(workflow)
    
    # 2. Create Tasks
    tasks = []
    for task_in in workflow_in.tasks:
        task = Task(
            workflow_id=workflow.id,
            name=task_in.name,
            action_type=task_in.action_type,
            action_payload=task_in.action_payload,
            dependencies=task_in.dependencies
        )
        session.add(task)
        tasks.append(task)
    
    await session.commit()
    
    # 3. Validate DAG structure
    try:
        DAGExecutor.validate_dag(tasks)
    except ValueError as e:
        # Rollback and return error
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    
    # Reload workflow with tasks
    statement = select(Workflow).where(Workflow.id == workflow.id).options(selectinload(Workflow.tasks))
    result = await session.exec(statement)
    workflow = result.one()
        
    return workflow

@router.get("/", response_model=List[WorkflowRead])
async def read_workflows(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    result = await session.exec(select(Workflow).options(selectinload(Workflow.tasks)).offset(skip).limit(limit))
    workflows = result.all()
    return workflows

@router.get("/{workflow_id}", response_model=WorkflowRead)
async def get_workflow(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session)
):
    statement = select(Workflow).where(Workflow.id == workflow_id).options(selectinload(Workflow.tasks))
    result = await session.exec(statement)
    workflow = result.first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    return workflow

@router.post("/{workflow_id}/execute")
async def execute_workflow(
    workflow_id: UUID,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session)
):
    # Verify workflow exists
    statement = select(Workflow).where(Workflow.id == workflow_id)
    result = await session.exec(statement)
    workflow = result.first()
    
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")
    
    if workflow.status == "running":
        raise HTTPException(status_code=400, detail="Workflow is already running")
    
    # Execute workflow in background
    background_tasks.add_task(execute_workflow_task, workflow_id)
    
    return {
        "workflow_id": str(workflow_id),
        "status": "queued",
        "message": "Workflow execution started"
    }

async def execute_workflow_task(workflow_id: UUID):
    """Background task to execute workflow."""
    from orbit.db.session import engine
    from sqlmodel.ext.asyncio.session import AsyncSession
    from sqlalchemy.orm import sessionmaker
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        runner = TaskRunner(session, ws_manager)
        await runner.execute_workflow(workflow_id)
