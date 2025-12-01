"""
Authentication and authorization models.
"""

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from sqlmodel import Field, SQLModel, Relationship
from sqlalchemy import Column, JSON


class User(SQLModel, table=True):
    """User model for authentication."""

    __tablename__ = "user"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    email: str = Field(unique=True, index=True)
    username: str = Field(unique=True, index=True)
    hashed_password: str
    full_name: Optional[str] = None
    
    # Status
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)
    
    # Roles and permissions
    roles: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None


class APIKey(SQLModel, table=True):
    """API Key for programmatic access."""

    __tablename__ = "apikey"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: UUID = Field(foreign_key="user.id", index=True)
    
    # Key details
    name: str = Field(description="Friendly name for the key")
    key_hash: str = Field(unique=True, index=True, description="Hashed API key")
    key_prefix: str = Field(description="First 8 chars for identification")
    
    # Permissions
    scopes: List[str] = Field(default=[], sa_column=Column(JSON))
    
    # Status
    is_active: bool = Field(default=True)
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None


class AuditLog(SQLModel, table=True):
    """Audit log for security events."""

    __tablename__ = "auditlog"

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    user_id: Optional[UUID] = Field(default=None, foreign_key="user.id", index=True)
    
    # Event details
    event_type: str = Field(index=True, description="login, logout, create, update, delete, etc.")
    resource_type: Optional[str] = Field(default=None, description="workflow, task, etc.")
    resource_id: Optional[UUID] = Field(default=None)
    
    # Request details
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    
    # Event data
    details: Optional[dict] = Field(default=None, sa_column=Column(JSON))
    
    # Status
    success: bool = Field(default=True)
    error_message: Optional[str] = None
    
    # Timestamp
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
