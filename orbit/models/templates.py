"""
Workflow template models.
Enables reusable workflow definitions with parameterization.
"""

from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Text
from sqlmodel import Field, SQLModel


class WorkflowTemplate(SQLModel, table=True):
    """
    Reusable workflow template.
    Can be instantiated with different parameters.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    name: str = Field(index=True, unique=True)
    description: str | None = Field(default=None, sa_column=Column(Text))
    category: str | None = Field(default=None, index=True)

    # Template definition
    template_data: dict[str, Any] = Field(sa_column=Column(JSON))

    # Parameters
    parameters: dict[str, Any] = Field(
        default={},
        sa_column=Column(JSON),
        description="Parameter definitions with defaults and validation"
    )

    # Metadata
    version: str = Field(default="1.0.0")
    author: str | None = Field(default=None)
    tags: list[str] = Field(default=[], sa_column=Column(JSON))

    # Usage tracking
    usage_count: int = Field(default=0)
    last_used_at: datetime | None = Field(default=None)

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Validation
    is_active: bool = Field(default=True)
    is_public: bool = Field(default=False)


class TemplateParameter(SQLModel):
    """
    Parameter definition for workflow template.
    """

    name: str
    type: str  # string, integer, float, boolean, array, object
    description: str | None = None
    default: Any | None = None
    required: bool = False
    validation: dict[str, Any] | None = None  # min, max, pattern, enum, etc.
