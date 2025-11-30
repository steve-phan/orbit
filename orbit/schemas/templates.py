"""
Pydantic schemas for workflow templates.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class TemplateParameterSchema(BaseModel):
    """Schema for template parameter definition."""

    name: str
    type: str = Field(..., description="Parameter type: string, integer, float, boolean, array, object")
    description: str | None = None
    default: Any | None = None
    required: bool = False
    validation: dict[str, Any] | None = None


class TemplateCreate(BaseModel):
    """Schema for creating a template."""

    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template_data: dict[str, Any] = Field(..., description="Workflow definition with placeholders")
    parameters: dict[str, Any] | None = Field(default={}, description="Parameter definitions")
    category: str | None = None
    tags: list[str] | None = Field(default=[])


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""

    description: str | None = None
    template_data: dict[str, Any] | None = None
    parameters: dict[str, Any] | None = None
    category: str | None = None
    tags: list[str] | None = None
    is_active: bool | None = None


class TemplateRead(BaseModel):
    """Schema for reading a template."""

    id: UUID
    name: str
    description: str | None
    category: str | None
    version: str
    tags: list[str]
    usage_count: int
    last_used_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class TemplateInstantiate(BaseModel):
    """Schema for instantiating a template."""

    parameters: dict[str, Any] = Field(..., description="Parameter values")
    workflow_name: str | None = Field(None, description="Override workflow name")
