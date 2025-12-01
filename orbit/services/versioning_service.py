"""
Workflow versioning service.
Manages version control for workflows with rollback capability.
"""

import hashlib
import json
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlmodel import desc, select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.logging import get_logger
from orbit.models.versioning import WorkflowChangeLog, WorkflowVersion
from orbit.models.workflow import Workflow

logger = get_logger("services.versioning")


class VersioningService:
    """
    Service for managing workflow versions.
    Provides version control, change tracking, and rollback capabilities.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    def _calculate_checksum(self, workflow_data: dict[str, Any]) -> str:
        """Calculate SHA256 checksum of workflow data."""
        data_str = json.dumps(workflow_data, sort_keys=True)
        return hashlib.sha256(data_str.encode()).hexdigest()

    def _calculate_diff(
        self, old_data: dict[str, Any] | None, new_data: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Calculate differences between two workflow definitions.

        Returns:
            Dictionary with added, removed, and modified fields
        """
        if old_data is None:
            return {"change_type": "created", "added": new_data}

        changes = {
            "added": {},
            "removed": {},
            "modified": {},
        }

        # Find added and modified
        for key, new_value in new_data.items():
            if key not in old_data:
                changes["added"][key] = new_value
            elif old_data[key] != new_value:
                changes["modified"][key] = {
                    "old": old_data[key],
                    "new": new_value,
                }

        # Find removed
        for key in old_data:
            if key not in new_data:
                changes["removed"][key] = old_data[key]

        return changes

    async def create_version(
        self,
        workflow: Workflow,
        change_summary: str | None = None,
        changed_by: str | None = None,
        version_tag: str | None = None,
        is_draft: bool = False,
    ) -> WorkflowVersion:
        """
        Create a new version of a workflow.

        Args:
            workflow: Workflow instance
            change_summary: Summary of changes
            changed_by: User who made the change
            version_tag: Optional version tag (e.g., 'v1.0.0')
            is_draft: Whether this is a draft version

        Returns:
            Created WorkflowVersion
        """
        # Get current version number
        statement = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow.id)
            .order_by(desc(WorkflowVersion.version_number))
        )
        result = await self.session.exec(statement)
        latest_version = result.first()

        version_number = 1 if latest_version is None else latest_version.version_number + 1

        # Prepare workflow data
        workflow_data = {
            "name": workflow.name,
            "description": workflow.description,
            "tasks": [
                {
                    "name": task.name,
                    "action_type": task.action_type,
                    "action_payload": task.action_payload,
                    "dependencies": task.dependencies,
                    "retry_policy": task.retry_policy,
                    "timeout_seconds": task.timeout_seconds,
                }
                for task in workflow.tasks
            ],
        }

        # Calculate checksum
        checksum = self._calculate_checksum(workflow_data)

        # Check if this version already exists (duplicate)
        if latest_version and latest_version.checksum == checksum:
            logger.info(f"Workflow {workflow.id} unchanged, skipping version creation")
            return latest_version

        # Deactivate previous active version if not draft
        if not is_draft and latest_version and latest_version.is_active:
            latest_version.is_active = False
            self.session.add(latest_version)

        # Create new version
        new_version = WorkflowVersion(
            workflow_id=workflow.id,
            version_number=version_number,
            version_tag=version_tag,
            name=workflow.name,
            description=workflow.description,
            workflow_data=workflow_data,
            change_summary=change_summary,
            changed_by=changed_by,
            is_active=not is_draft,
            is_draft=is_draft,
            checksum=checksum,
            activated_at=datetime.utcnow() if not is_draft else None,
        )

        self.session.add(new_version)

        # Create change log
        old_data = latest_version.workflow_data if latest_version else None
        changes = self._calculate_diff(old_data, workflow_data)

        change_log = WorkflowChangeLog(
            workflow_id=workflow.id,
            from_version=latest_version.version_number if latest_version else None,
            to_version=version_number,
            change_type="created" if latest_version is None else "updated",
            changes=changes,
            changed_by=changed_by,
            change_reason=change_summary,
        )

        self.session.add(change_log)
        await self.session.commit()
        await self.session.refresh(new_version)

        logger.info(
            f"Created version {version_number} for workflow {workflow.id} "
            f"(draft={is_draft})"
        )

        return new_version

    async def get_version(
        self, workflow_id: UUID, version_number: int
    ) -> WorkflowVersion | None:
        """Get a specific version of a workflow."""
        statement = select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.version_number == version_number,
        )
        result = await self.session.exec(statement)
        return result.first()

    async def get_active_version(self, workflow_id: UUID) -> WorkflowVersion | None:
        """Get the currently active version of a workflow."""
        statement = select(WorkflowVersion).where(
            WorkflowVersion.workflow_id == workflow_id,
            WorkflowVersion.is_active == True,  # noqa: E712
        )
        result = await self.session.exec(statement)
        return result.first()

    async def list_versions(
        self,
        workflow_id: UUID,
        include_drafts: bool = False,
        limit: int = 50,
    ) -> list[WorkflowVersion]:
        """
        List all versions of a workflow.

        Args:
            workflow_id: Workflow UUID
            include_drafts: Include draft versions
            limit: Maximum number of versions to return

        Returns:
            List of WorkflowVersion ordered by version number (descending)
        """
        statement = (
            select(WorkflowVersion)
            .where(WorkflowVersion.workflow_id == workflow_id)
            .order_by(desc(WorkflowVersion.version_number))
            .limit(limit)
        )

        if not include_drafts:
            statement = statement.where(WorkflowVersion.is_draft == False)  # noqa: E712

        result = await self.session.exec(statement)
        return list(result.all())

    async def rollback_to_version(
        self,
        workflow_id: UUID,
        version_number: int,
        changed_by: str | None = None,
    ) -> tuple[Workflow, WorkflowVersion]:
        """
        Rollback workflow to a specific version.

        Args:
            workflow_id: Workflow UUID
            version_number: Version number to rollback to
            changed_by: User performing the rollback

        Returns:
            Tuple of (updated Workflow, new WorkflowVersion)
        """
        # Get target version
        target_version = await self.get_version(workflow_id, version_number)
        if not target_version:
            raise ValueError(f"Version {version_number} not found")

        # Get current workflow
        workflow_statement = select(Workflow).where(Workflow.id == workflow_id)
        workflow_result = await self.session.exec(workflow_statement)
        workflow = workflow_result.first()

        if not workflow:
            raise ValueError(f"Workflow {workflow_id} not found")

        # Update workflow with target version data
        workflow.name = target_version.name
        workflow.description = target_version.description

        # Note: Task restoration would require more complex logic
        # For now, we create a new version pointing to the old data

        self.session.add(workflow)

        # Create new version (rollback)
        new_version = await self.create_version(
            workflow=workflow,
            change_summary=f"Rolled back to version {version_number}",
            changed_by=changed_by,
        )

        # Create rollback change log
        change_log = WorkflowChangeLog(
            workflow_id=workflow_id,
            from_version=new_version.version_number - 1,
            to_version=new_version.version_number,
            change_type="rolled_back",
            changes={"rolled_back_to": version_number},
            changed_by=changed_by,
            change_reason=f"Rolled back to version {version_number}",
        )

        self.session.add(change_log)
        await self.session.commit()

        logger.info(
            f"Rolled back workflow {workflow_id} to version {version_number}"
        )

        return workflow, new_version

    async def get_change_log(
        self, workflow_id: UUID, limit: int = 50
    ) -> list[WorkflowChangeLog]:
        """Get change log for a workflow."""
        statement = (
            select(WorkflowChangeLog)
            .where(WorkflowChangeLog.workflow_id == workflow_id)
            .order_by(desc(WorkflowChangeLog.created_at))
            .limit(limit)
        )

        result = await self.session.exec(statement)
        return list(result.all())

    async def compare_versions(
        self, workflow_id: UUID, version_a: int, version_b: int
    ) -> dict[str, Any]:
        """
        Compare two versions of a workflow.

        Returns:
            Dictionary with differences between versions
        """
        ver_a = await self.get_version(workflow_id, version_a)
        ver_b = await self.get_version(workflow_id, version_b)

        if not ver_a or not ver_b:
            raise ValueError("One or both versions not found")

        return self._calculate_diff(ver_a.workflow_data, ver_b.workflow_data)
