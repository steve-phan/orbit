"""
API endpoints for workflow versioning.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.logging import get_logger
from orbit.db.session import get_session
from orbit.repositories.workflow_repository import WorkflowRepository
from orbit.schemas.versioning import (
    ChangeLogRead,
    VersionCompare,
    VersionCreate,
    VersionListItem,
    VersionRead,
    VersionRollback,
)
from orbit.services.versioning_service import VersioningService

logger = get_logger("api.versioning")
router = APIRouter()


@router.post("/{workflow_id}/versions", response_model=VersionRead, status_code=201)
async def create_version(
    workflow_id: UUID,
    version_in: VersionCreate,
    session: AsyncSession = Depends(get_session),
):
    """
    Create a new version of a workflow.

    This captures the current state of the workflow as a version.
    """
    # Get workflow
    workflow_repo = WorkflowRepository(session)
    workflow = await workflow_repo.get_by_id(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="Workflow not found")

    # Create version
    versioning_service = VersioningService(session)
    version = await versioning_service.create_version(
        workflow=workflow,
        change_summary=version_in.change_summary,
        changed_by=version_in.changed_by,
        version_tag=version_in.version_tag,
        is_draft=version_in.is_draft,
    )

    return version


@router.get("/{workflow_id}/versions", response_model=list[VersionListItem])
async def list_versions(
    workflow_id: UUID,
    include_drafts: bool = Query(default=False),
    limit: int = Query(default=50, le=100),
    session: AsyncSession = Depends(get_session),
):
    """List all versions of a workflow."""
    versioning_service = VersioningService(session)
    versions = await versioning_service.list_versions(
        workflow_id=workflow_id,
        include_drafts=include_drafts,
        limit=limit,
    )

    return versions


@router.get("/{workflow_id}/versions/active", response_model=VersionRead)
async def get_active_version(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get the currently active version of a workflow."""
    versioning_service = VersioningService(session)
    version = await versioning_service.get_active_version(workflow_id)

    if not version:
        raise HTTPException(status_code=404, detail="No active version found")

    return version


@router.get("/{workflow_id}/versions/{version_number}", response_model=VersionRead)
async def get_version(
    workflow_id: UUID,
    version_number: int,
    session: AsyncSession = Depends(get_session),
):
    """Get a specific version of a workflow."""
    versioning_service = VersioningService(session)
    version = await versioning_service.get_version(workflow_id, version_number)

    if not version:
        raise HTTPException(status_code=404, detail="Version not found")

    return version


@router.post("/{workflow_id}/rollback", response_model=VersionRead)
async def rollback_version(
    workflow_id: UUID,
    rollback_in: VersionRollback,
    session: AsyncSession = Depends(get_session),
):
    """
    Rollback workflow to a specific version.

    This creates a new version that restores the workflow to a previous state.
    """
    versioning_service = VersioningService(session)

    try:
        workflow, new_version = await versioning_service.rollback_to_version(
            workflow_id=workflow_id,
            version_number=rollback_in.version_number,
            changed_by=rollback_in.changed_by,
        )

        return new_version

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{workflow_id}/changelog", response_model=list[ChangeLogRead])
async def get_changelog(
    workflow_id: UUID,
    limit: int = Query(default=50, le=100),
    session: AsyncSession = Depends(get_session),
):
    """Get change log for a workflow."""
    versioning_service = VersioningService(session)
    changelog = await versioning_service.get_change_log(workflow_id, limit=limit)

    return changelog


@router.get("/{workflow_id}/compare", response_model=VersionCompare)
async def compare_versions(
    workflow_id: UUID,
    version_a: int = Query(..., description="First version to compare"),
    version_b: int = Query(..., description="Second version to compare"),
    session: AsyncSession = Depends(get_session),
):
    """Compare two versions of a workflow."""
    versioning_service = VersioningService(session)

    try:
        differences = await versioning_service.compare_versions(
            workflow_id=workflow_id,
            version_a=version_a,
            version_b=version_b,
        )

        return VersionCompare(
            version_a=version_a,
            version_b=version_b,
            differences=differences,
        )

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
