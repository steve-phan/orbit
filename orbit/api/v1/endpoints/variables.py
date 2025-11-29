"""
API endpoints for workflow variables and secrets.
"""

from uuid import UUID
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.db.session import get_session
from orbit.services.variable_service import VariableService
from orbit.schemas.variables import (
    VariableCreate,
    VariableRead,
    SecretCreate,
    SecretRead,
)
from orbit.core.logging import get_logger

logger = get_logger("api.variables")
router = APIRouter()


# Workflow Variables
@router.post("/{workflow_id}/variables", response_model=VariableRead, status_code=201)
async def create_workflow_variable(
    workflow_id: UUID,
    variable_in: VariableCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create a workflow variable."""
    service = VariableService(session)
    variable = await service.create_workflow_variable(
        workflow_id=workflow_id,
        key=variable_in.key,
        value=variable_in.value,
        description=variable_in.description,
    )
    return variable


@router.get("/{workflow_id}/variables", response_model=List[VariableRead])
async def get_workflow_variables(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get all variables for a workflow."""
    service = VariableService(session)
    variables = await service.get_workflow_variables(workflow_id)
    return variables


@router.delete("/{workflow_id}/variables/{key}", status_code=204)
async def delete_workflow_variable(
    workflow_id: UUID,
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a workflow variable."""
    service = VariableService(session)
    deleted = await service.delete_workflow_variable(workflow_id, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Variable not found")
    return None


# Workflow Secrets
@router.post("/{workflow_id}/secrets", response_model=SecretRead, status_code=201)
async def create_workflow_secret(
    workflow_id: UUID,
    secret_in: SecretCreate,
    session: AsyncSession = Depends(get_session),
):
    """Create an encrypted workflow secret."""
    service = VariableService(session)
    secret = await service.create_workflow_secret(
        workflow_id=workflow_id,
        key=secret_in.key,
        value=secret_in.value,
        description=secret_in.description,
    )
    return SecretRead(
        id=secret.id,
        key=secret.key,
        value_masked="***ENCRYPTED***",
        description=secret.description,
    )


@router.get("/{workflow_id}/secrets", response_model=List[SecretRead])
async def get_workflow_secrets(
    workflow_id: UUID,
    session: AsyncSession = Depends(get_session),
):
    """Get all secrets for a workflow (values are masked)."""
    service = VariableService(session)
    secrets = await service.get_workflow_secrets(workflow_id)
    return [
        SecretRead(
            id=secret.id,
            key=secret.key,
            value_masked="***ENCRYPTED***",
            description=secret.description,
        )
        for secret in secrets
    ]


@router.delete("/{workflow_id}/secrets/{key}", status_code=204)
async def delete_workflow_secret(
    workflow_id: UUID,
    key: str,
    session: AsyncSession = Depends(get_session),
):
    """Delete a workflow secret."""
    service = VariableService(session)
    deleted = await service.delete_workflow_secret(workflow_id, key)
    if not deleted:
        raise HTTPException(status_code=404, detail="Secret not found")
    return None
