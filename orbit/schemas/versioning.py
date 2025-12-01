"""
Pydantic schemas for workflow versioning.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class VersionCreate(BaseModel):
    """Schema for creating a new version."""
    
    change_summary: Optional[str] = Field(None, description="Summary of changes")
    changed_by: Optional[str] = Field(None, description="User making the change")
    version_tag: Optional[str] = Field(None, description="Version tag (e.g., 'v1.0.0')")
    is_draft: bool = Field(False, description="Create as draft version")


class VersionRead(BaseModel):
    """Schema for reading a version."""
    
    id: UUID
    workflow_id: UUID
    version_number: int
    version_tag: Optional[str]
    name: str
    description: Optional[str]
    change_summary: Optional[str]
    changed_by: Optional[str]
    is_active: bool
    is_draft: bool
    created_at: datetime
    activated_at: Optional[datetime]
    checksum: str
    
    class Config:
        from_attributes = True


class VersionListItem(BaseModel):
    """Schema for version list item (without full workflow_data)."""
    
    id: UUID
    version_number: int
    version_tag: Optional[str]
    name: str
    change_summary: Optional[str]
    changed_by: Optional[str]
    is_active: bool
    is_draft: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class VersionRollback(BaseModel):
    """Schema for rolling back to a version."""
    
    version_number: int = Field(..., description="Version number to rollback to")
    changed_by: Optional[str] = Field(None, description="User performing rollback")


class ChangeLogRead(BaseModel):
    """Schema for reading change log."""
    
    id: UUID
    workflow_id: UUID
    from_version: Optional[int]
    to_version: int
    change_type: str
    changes: Dict[str, Any]
    changed_by: Optional[str]
    change_reason: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


class VersionCompare(BaseModel):
    """Schema for version comparison result."""
    
    version_a: int
    version_b: int
    differences: Dict[str, Any]
