"""
Pydantic schemas for workflow templates.
"""

from typing import Optional, Dict, Any, List
from uuid import UUID
from pydantic import BaseModel, Field
from datetime import datetime


class TemplateParameterSchema(BaseModel):
    """Schema for template parameter definition."""
    
    name: str
    type: str = Field(..., description="Parameter type: string, integer, float, boolean, array, object")
    description: Optional[str] = None
    default: Optional[Any] = None
    required: bool = False
    validation: Optional[Dict[str, Any]] = None


class TemplateCreate(BaseModel):
    """Schema for creating a template."""
    
    name: str = Field(..., description="Template name")
    description: str = Field(..., description="Template description")
    template_data: Dict[str, Any] = Field(..., description="Workflow definition with placeholders")
    parameters: Optional[Dict[str, Any]] = Field(default={}, description="Parameter definitions")
    category: Optional[str] = None
    tags: Optional[List[str]] = Field(default=[])


class TemplateUpdate(BaseModel):
    """Schema for updating a template."""
    
    description: Optional[str] = None
    template_data: Optional[Dict[str, Any]] = None
    parameters: Optional[Dict[str, Any]] = None
    category: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class TemplateRead(BaseModel):
    """Schema for reading a template."""
    
    id: UUID
    name: str
    description: Optional[str]
    category: Optional[str]
    version: str
    tags: List[str]
    usage_count: int
    last_used_at: Optional[datetime]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class TemplateInstantiate(BaseModel):
    """Schema for instantiating a template."""
    
    parameters: Dict[str, Any] = Field(..., description="Parameter values")
    workflow_name: Optional[str] = Field(None, description="Override workflow name")
