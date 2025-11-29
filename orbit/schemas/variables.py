"""
Pydantic schemas for variables and secrets.
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class VariableCreate(BaseModel):
    """Schema for creating a variable."""

    key: str = Field(..., description="Variable key")
    value: str = Field(..., description="Variable value")
    description: Optional[str] = Field(None, description="Variable description")


class VariableUpdate(BaseModel):
    """Schema for updating a variable."""

    value: Optional[str] = Field(None, description="New value")
    description: Optional[str] = Field(None, description="New description")


class VariableRead(BaseModel):
    """Schema for reading a variable."""

    id: UUID
    key: str
    value: str
    description: Optional[str] = None

    class Config:
        from_attributes = True


class SecretCreate(BaseModel):
    """Schema for creating a secret."""

    key: str = Field(..., description="Secret key")
    value: str = Field(..., description="Secret value (will be encrypted)")
    description: Optional[str] = Field(None, description="Secret description")


class SecretUpdate(BaseModel):
    """Schema for updating a secret."""

    value: Optional[str] = Field(None, description="New value (will be encrypted)")
    description: Optional[str] = Field(None, description="New description")


class SecretRead(BaseModel):
    """Schema for reading a secret (value is masked)."""

    id: UUID
    key: str
    value_masked: str = Field(default="***ENCRYPTED***", description="Masked value")
    description: Optional[str] = None

    class Config:
        from_attributes = True
