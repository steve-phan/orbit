"""
API endpoints for workflow templates.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.logging import get_logger
from orbit.db.session import get_session
from orbit.repositories.workflow_repository import TaskRepository, WorkflowRepository
from orbit.schemas.templates import (
    TemplateCreate,
    TemplateInstantiate,
    TemplateRead,
)
from orbit.schemas.workflow import WorkflowRead
from orbit.services.template_service import TemplateService

logger = get_logger("api.templates")
router = APIRouter()


@router.post("/", response_model=TemplateRead, status_code=201)
async def create_template(
    template_in: TemplateCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a new workflow template."""
    service = TemplateService(session)

    # Check if template name already exists
    existing = await service.get_template_by_name(template_in.name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Template '{template_in.name}' already exists")

    template = await service.create_template(
        name=template_in.name,
        description=template_in.description,
        template_data=template_in.template_data,
        parameters=template_in.parameters,
        category=template_in.category,
        tags=template_in.tags,
    )

    return template


@router.get("/", response_model=list[TemplateRead])
async def list_templates(
    category: str | None = Query(default=None),
    tag: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    session: AsyncSession = Depends(get_session),
):
    """List all workflow templates."""
    service = TemplateService(session)
    templates = await service.list_templates(
        category=category,
        tag=tag,
        active_only=active_only,
    )
    return templates


@router.get("/{template_id}", response_model=TemplateRead)
async def get_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific template."""
    service = TemplateService(session)
    template = await service.get_template(template_id)

    if not template:
        raise HTTPException(status_code=404, detail="Template not found")

    return template


@router.post("/{template_id}/instantiate", response_model=WorkflowRead, status_code=201)
async def instantiate_template(
    template_id: UUID,
    instantiate_in: TemplateInstantiate,
    session: AsyncSession = Depends(get_session),
):
    """
    Instantiate a template to create a workflow.

    This creates a new workflow from the template with the provided parameters.
    """
    template_service = TemplateService(session)

    try:
        # Instantiate template
        workflow_create = await template_service.instantiate_template(
            template_id=template_id,
            parameters=instantiate_in.parameters,
            workflow_name=instantiate_in.workflow_name,
        )

        # Create workflow using workflow service
        workflow_repo = WorkflowRepository(session)
        task_repo = TaskRepository(session)
        from orbit.services.workflow_service import WorkflowService
        workflow_service = WorkflowService(workflow_repo, task_repo)
        workflow = await workflow_service.create_workflow(workflow_create)

        return workflow

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to instantiate template: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to instantiate template: {str(e)}")


@router.delete("/{template_id}", status_code=204)
async def delete_template(
    template_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Delete a template."""
    service = TemplateService(session)
    deleted = await service.delete_template(template_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="Template not found")

    return None
