"""
Workflow versioning models.
Enables version control for workflow definitions with rollback capability.
"""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON, Text


class WorkflowVersion(SQLModel, table=True):
    """
    Stores historical versions of workflow definitions.
    Enables version control and rollback capability.
    """

    __tablename__ = "workflowversion"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    
    # Version information
    version_number: int = Field(index=True, description="Sequential version number")
    version_tag: Optional[str] = Field(default=None, description="Optional version tag (e.g., 'v1.0.0')")
    
    # Workflow definition snapshot
    name: str
    description: Optional[str] = Field(default=None, sa_column=Column(Text))
    workflow_data: Dict[str, Any] = Field(sa_column=Column(JSON), description="Complete workflow definition")
    
    # Change tracking
    change_summary: Optional[str] = Field(default=None, sa_column=Column(Text))
    changed_by: Optional[str] = Field(default=None, description="User who made the change")
    
    # Status
    is_active: bool = Field(default=False, description="Currently active version")
    is_draft: bool = Field(default=False, description="Draft version (not deployed)")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    activated_at: Optional[datetime] = Field(default=None)
    
    # Metadata
    checksum: Optional[str] = Field(default=None, description="SHA256 hash of workflow_data")


class WorkflowChangeLog(SQLModel, table=True):
    """
    Detailed change log for workflow modifications.
    Tracks what changed between versions.
    """

    __tablename__ = "workflowchangelog"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    from_version: Optional[int] = Field(default=None, description="Previous version number")
    to_version: int = Field(description="New version number")
    
    # Change details
    change_type: str = Field(description="Type: created, updated, rolled_back, deleted")
    changes: Dict[str, Any] = Field(sa_column=Column(JSON), description="Detailed diff of changes")
    
    # Metadata
    changed_by: Optional[str] = Field(default=None)
    change_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
