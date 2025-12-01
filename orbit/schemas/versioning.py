"""
Pydantic schemas for workflow versioning.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class VersionCreate(BaseModel):
    """Schema for creating a new version."""

    change_summary: str | None = Field(None, description="Summary of changes")
    changed_by: str | None = Field(None, description="User making the change")
    version_tag: str | None = Field(None, description="Version tag (e.g., 'v1.0.0')")
    is_draft: bool = Field(False, description="Create as draft version")


class VersionRead(BaseModel):
    """Schema for reading a version."""

    id: UUID
    workflow_id: UUID
    version_number: int
    version_tag: str | None
    name: str
    description: str | None
    change_summary: str | None
    changed_by: str | None
    is_active: bool
    is_draft: bool
    created_at: datetime
    activated_at: datetime | None
    checksum: str

    class Config:
        from_attributes = True


class VersionListItem(BaseModel):
    """Schema for version list item (without full workflow_data)."""

    id: UUID
    version_number: int
    version_tag: str | None
    name: str
    change_summary: str | None
    changed_by: str | None
    is_active: bool
    is_draft: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VersionRollback(BaseModel):
    """Schema for rolling back to a version."""

    version_number: int = Field(..., description="Version number to rollback to")
    changed_by: str | None = Field(None, description="User performing rollback")


class ChangeLogRead(BaseModel):
    """Schema for reading change log."""

    id: UUID
    workflow_id: UUID
    from_version: int | None
    to_version: int
    change_type: str
    changes: dict[str, Any]
    changed_by: str | None
    change_reason: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class VersionCompare(BaseModel):
    """Schema for version comparison result."""

    version_a: int
    version_b: int
    differences: dict[str, Any]
