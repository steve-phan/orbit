"""
Workflow variables and secrets models.
Provides secure storage for workflow configuration.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, Text
from sqlmodel import Field, SQLModel


class WorkflowVariable(SQLModel, table=True):
    """
    Workflow-level variables.
    Used for parameterizing workflows without hardcoding values.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    key: str = Field(index=True)
    value: str = Field(sa_column=Column(Text))
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class WorkflowSecret(SQLModel, table=True):
    """
    Encrypted secrets for workflows.
    Values are encrypted at rest using Fernet encryption.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    key: str = Field(index=True)
    encrypted_value: str = Field(sa_column=Column(Text))
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GlobalVariable(SQLModel, table=True):
    """
    Global variables accessible to all workflows.
    Useful for system-wide configuration.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key: str = Field(unique=True, index=True)
    value: str = Field(sa_column=Column(Text))
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class GlobalSecret(SQLModel, table=True):
    """
    Global encrypted secrets accessible to all workflows.
    Values are encrypted at rest using Fernet encryption.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    key: str = Field(unique=True, index=True)
    encrypted_value: str = Field(sa_column=Column(Text))
    description: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
