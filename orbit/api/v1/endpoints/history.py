"""
API endpoints for execution history.
Provides audit trail and debugging capabilities.
"""

from uuid import UUID
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Query
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.db.session import get_session
from orbit.models.execution_history import WorkflowExecution, TaskExecution
from orbit.core.logging import get_logger

logger = get_logger("api.history")
router = APIRouter()


@router.get("/workflows/{workflow_id}/history")
async def get_workflow_execution_history(
    workflow_id: UUID,
    limit: int = Query(default=50, le=100),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Get execution history for a workflow.
    
    Args:
        workflow_id: Workflow UUID
        limit: Maximum number of results
        offset: Pagination offset
        status: Filter by status (queued, running, completed, failed, cancelled)
    """
    statement = select(WorkflowExecution).where(
        WorkflowExecution.workflow_id == workflow_id
    )
    
    if status:
        statement = statement.where(WorkflowExecution.status == status)
    
    statement = statement.order_by(WorkflowExecution.started_at.desc())
    statement = statement.offset(offset).limit(limit)
    
    result = await session.exec(statement)
    executions = result.all()
    
    return {
        "workflow_id": str(workflow_id),
        "total": len(executions),
        "executions": [
            {
                "id": str(exec.id),
                "workflow_name": exec.workflow_name,
                "status": exec.status,
                "started_at": exec.started_at.isoformat(),
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "duration_seconds": exec.duration_seconds,
                "error_message": exec.error_message,
            }
            for exec in executions
        ],
    }


@router.get("/workflows/{workflow_id}/executions/{execution_id}")
async def get_workflow_execution_details(
    workflow_id: UUID,
    execution_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get detailed information about a specific execution."""
    # Get workflow execution
    workflow_statement = select(WorkflowExecution).where(
        WorkflowExecution.id == execution_id,
        WorkflowExecution.workflow_id == workflow_id,
    )
    workflow_result = await session.exec(workflow_statement)
    workflow_exec = workflow_result.first()
    
    if not workflow_exec:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Execution not found")
    
    # Get task executions
    task_statement = select(TaskExecution).where(
        TaskExecution.workflow_execution_id == execution_id
    ).order_by(TaskExecution.started_at)
    
    task_result = await session.exec(task_statement)
    task_execs = task_result.all()
    
    return {
        "id": str(workflow_exec.id),
        "workflow_id": str(workflow_exec.workflow_id),
        "workflow_name": workflow_exec.workflow_name,
        "status": workflow_exec.status,
        "started_at": workflow_exec.started_at.isoformat(),
        "completed_at": workflow_exec.completed_at.isoformat() if workflow_exec.completed_at else None,
        "duration_seconds": workflow_exec.duration_seconds,
        "error_message": workflow_exec.error_message,
        "metadata": workflow_exec.metadata,
        "tasks": [
            {
                "id": str(task.id),
                "task_name": task.task_name,
                "attempt_number": task.attempt_number,
                "status": task.status,
                "started_at": task.started_at.isoformat(),
                "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                "duration_seconds": task.duration_seconds,
                "error_message": task.error_message,
                "result": task.result,
            }
            for task in task_execs
        ],
    }


@router.get("/history/recent")
async def get_recent_executions(
    limit: int = Query(default=20, le=100),
    hours: int = Query(default=24, le=168),  # Max 1 week
    status: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_session),
):
    """
    Get recent workflow executions across all workflows.
    
    Args:
        limit: Maximum number of results
        hours: Look back this many hours
        status: Filter by status
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    statement = select(WorkflowExecution).where(
        WorkflowExecution.started_at >= cutoff_time
    )
    
    if status:
        statement = statement.where(WorkflowExecution.status == status)
    
    statement = statement.order_by(WorkflowExecution.started_at.desc())
    statement = statement.limit(limit)
    
    result = await session.exec(statement)
    executions = result.all()
    
    return {
        "period_hours": hours,
        "total": len(executions),
        "executions": [
            {
                "id": str(exec.id),
                "workflow_id": str(exec.workflow_id),
                "workflow_name": exec.workflow_name,
                "status": exec.status,
                "started_at": exec.started_at.isoformat(),
                "completed_at": exec.completed_at.isoformat() if exec.completed_at else None,
                "duration_seconds": exec.duration_seconds,
                "error_message": exec.error_message,
            }
            for exec in executions
        ],
    }


@router.get("/history/stats")
async def get_execution_stats(
    hours: int = Query(default=24, le=168),
    session: AsyncSession = Depends(get_session),
):
    """
    Get execution statistics.
    
    Args:
        hours: Look back this many hours
    """
    cutoff_time = datetime.utcnow() - timedelta(hours=hours)
    
    statement = select(WorkflowExecution).where(
        WorkflowExecution.started_at >= cutoff_time
    )
    
    result = await session.exec(statement)
    executions = list(result.all())
    
    # Calculate stats
    total = len(executions)
    completed = sum(1 for e in executions if e.status == "completed")
    failed = sum(1 for e in executions if e.status == "failed")
    running = sum(1 for e in executions if e.status == "running")
    cancelled = sum(1 for e in executions if e.status == "cancelled")
    
    # Calculate average duration for completed workflows
    completed_execs = [e for e in executions if e.status == "completed" and e.duration_seconds]
    avg_duration = (
        sum(e.duration_seconds for e in completed_execs) / len(completed_execs)
        if completed_execs
        else 0
    )
    
    success_rate = (completed / total * 100) if total > 0 else 0
    
    return {
        "period_hours": hours,
        "total_executions": total,
        "completed": completed,
        "failed": failed,
        "running": running,
        "cancelled": cancelled,
        "success_rate": round(success_rate, 2),
        "average_duration_seconds": round(avg_duration, 2),
    }
