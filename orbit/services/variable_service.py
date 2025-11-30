"""
Service for managing workflow variables and secrets.
Handles encryption/decryption and variable interpolation.
"""

import re
from typing import Any
from uuid import UUID

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.encryption import encryption_service
from orbit.core.logging import get_logger
from orbit.models.variables import (
    GlobalSecret,
    GlobalVariable,
    WorkflowSecret,
    WorkflowVariable,
)

logger = get_logger("services.variables")


class VariableService:
    """
    Service for managing variables and secrets.
    Provides encryption, decryption, and variable interpolation.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # Workflow Variables
    async def create_workflow_variable(
        self, workflow_id: UUID, key: str, value: str, description: str | None = None
    ) -> WorkflowVariable:
        """Create a workflow variable."""
        variable = WorkflowVariable(
            workflow_id=workflow_id, key=key, value=value, description=description
        )
        self.session.add(variable)
        await self.session.commit()
        await self.session.refresh(variable)
        logger.info(f"Created workflow variable: {key} for workflow {workflow_id}")
        return variable

    async def get_workflow_variables(
        self, workflow_id: UUID
    ) -> list[WorkflowVariable]:
        """Get all variables for a workflow."""
        statement = select(WorkflowVariable).where(
            WorkflowVariable.workflow_id == workflow_id
        )
        result = await self.session.exec(statement)
        return list(result.all())

    async def get_workflow_variable(
        self, workflow_id: UUID, key: str
    ) -> WorkflowVariable | None:
        """Get a specific workflow variable."""
        statement = select(WorkflowVariable).where(
            WorkflowVariable.workflow_id == workflow_id,
            WorkflowVariable.key == key,
        )
        result = await self.session.exec(statement)
        return result.first()

    async def delete_workflow_variable(self, workflow_id: UUID, key: str) -> bool:
        """Delete a workflow variable."""
        variable = await self.get_workflow_variable(workflow_id, key)
        if variable:
            await self.session.delete(variable)
            await self.session.commit()
            logger.info(f"Deleted workflow variable: {key}")
            return True
        return False

    # Workflow Secrets
    async def create_workflow_secret(
        self, workflow_id: UUID, key: str, value: str, description: str | None = None
    ) -> WorkflowSecret:
        """Create an encrypted workflow secret."""
        encrypted_value = encryption_service.encrypt(value)
        secret = WorkflowSecret(
            workflow_id=workflow_id,
            key=key,
            encrypted_value=encrypted_value,
            description=description,
        )
        self.session.add(secret)
        await self.session.commit()
        await self.session.refresh(secret)
        logger.info(f"Created workflow secret: {key} for workflow {workflow_id}")
        return secret

    async def get_workflow_secrets(self, workflow_id: UUID) -> list[WorkflowSecret]:
        """Get all secrets for a workflow (encrypted)."""
        statement = select(WorkflowSecret).where(
            WorkflowSecret.workflow_id == workflow_id
        )
        result = await self.session.exec(statement)
        return list(result.all())

    async def get_workflow_secret_value(
        self, workflow_id: UUID, key: str
    ) -> str | None:
        """Get decrypted secret value."""
        statement = select(WorkflowSecret).where(
            WorkflowSecret.workflow_id == workflow_id, WorkflowSecret.key == key
        )
        result = await self.session.exec(statement)
        secret = result.first()

        if secret:
            try:
                return encryption_service.decrypt(secret.encrypted_value)
            except Exception as e:
                logger.error(f"Failed to decrypt secret {key}: {e}")
                return None
        return None

    async def delete_workflow_secret(self, workflow_id: UUID, key: str) -> bool:
        """Delete a workflow secret."""
        statement = select(WorkflowSecret).where(
            WorkflowSecret.workflow_id == workflow_id, WorkflowSecret.key == key
        )
        result = await self.session.exec(statement)
        secret = result.first()

        if secret:
            await self.session.delete(secret)
            await self.session.commit()
            logger.info(f"Deleted workflow secret: {key}")
            return True
        return False

    # Global Variables
    async def create_global_variable(
        self, key: str, value: str, description: str | None = None
    ) -> GlobalVariable:
        """Create a global variable."""
        variable = GlobalVariable(key=key, value=value, description=description)
        self.session.add(variable)
        await self.session.commit()
        await self.session.refresh(variable)
        logger.info(f"Created global variable: {key}")
        return variable

    async def get_global_variable(self, key: str) -> GlobalVariable | None:
        """Get a global variable."""
        statement = select(GlobalVariable).where(GlobalVariable.key == key)
        result = await self.session.exec(statement)
        return result.first()

    # Variable Interpolation
    async def interpolate_variables(
        self, text: str, workflow_id: UUID | None = None
    ) -> str:
        """
        Replace variable placeholders in text with actual values.

        Supports:
        - ${var:key} - Workflow variable
        - ${secret:key} - Workflow secret
        - ${global:key} - Global variable
        - ${global_secret:key} - Global secret

        Args:
            text: Text with variable placeholders
            workflow_id: Workflow ID for workflow-specific variables

        Returns:
            Text with variables interpolated
        """
        # Find all variable references
        pattern = r'\$\{([^:]+):([^}]+)\}'
        matches = re.findall(pattern, text)

        result = text
        for var_type, var_key in matches:
            value = None

            if var_type == "var" and workflow_id:
                variable = await self.get_workflow_variable(workflow_id, var_key)
                value = variable.value if variable else None

            elif var_type == "secret" and workflow_id:
                value = await self.get_workflow_secret_value(workflow_id, var_key)

            elif var_type == "global":
                variable = await self.get_global_variable(var_key)
                value = variable.value if variable else None

            elif var_type == "global_secret":
                statement = select(GlobalSecret).where(GlobalSecret.key == var_key)
                result_obj = await self.session.exec(statement)
                secret = result_obj.first()
                if secret:
                    try:
                        value = encryption_service.decrypt(secret.encrypted_value)
                    except Exception as e:
                        logger.error(f"Failed to decrypt global secret {var_key}: {e}")

            if value is not None:
                placeholder = f"${{{var_type}:{var_key}}}"
                result = result.replace(placeholder, value)
            else:
                logger.warning(
                    f"Variable not found: {var_type}:{var_key}, leaving placeholder"
                )

        return result

    async def interpolate_dict(
        self, data: dict[str, Any], workflow_id: UUID | None = None
    ) -> dict[str, Any]:
        """
        Recursively interpolate variables in a dictionary.

        Args:
            data: Dictionary with potential variable placeholders
            workflow_id: Workflow ID for workflow-specific variables

        Returns:
            Dictionary with variables interpolated
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = await self.interpolate_variables(value, workflow_id)
            elif isinstance(value, dict):
                result[key] = await self.interpolate_dict(value, workflow_id)
            elif isinstance(value, list):
                result[key] = [
                    await self.interpolate_variables(item, workflow_id)
                    if isinstance(item, str)
                    else item
                    for item in value
                ]
            else:
                result[key] = value

        return result
