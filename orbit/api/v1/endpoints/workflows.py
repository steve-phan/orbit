from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import List

from orbit.db.session import get_session
from orbit.models.workflow import Workflow, Task
from orbit.schemas.workflow import WorkflowCreate, WorkflowRead, TaskCreate

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
    
    # Refresh to get IDs
    for task in tasks:
        await session.refresh(task)
        
    return workflow

@router.get("/", response_model=List[WorkflowRead])
async def read_workflows(
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session)
):
    result = await session.exec(select(Workflow).offset(skip).limit(limit))
    workflows = result.all()
    return workflows
