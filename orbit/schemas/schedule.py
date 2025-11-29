"""
Pydantic schemas for workflow schedules.
"""

from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field, field_validator
from croniter import croniter


class ScheduleCreate(BaseModel):
    """Schema for creating a workflow schedule."""

    cron_expression: str = Field(
        ..., description="Cron expression (e.g., '0 2 * * *' for daily at 2 AM)"
    )
    timezone: str = Field(default="UTC", description="Timezone for schedule")
    enabled: bool = Field(default=True, description="Schedule enabled")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str) -> str:
        """Validate cron expression."""
        try:
            croniter(v)
            return v
        except (ValueError, KeyError) as e:
            raise ValueError(f"Invalid cron expression: {v}") from e


class ScheduleUpdate(BaseModel):
    """Schema for updating a workflow schedule."""

    cron_expression: Optional[str] = Field(
        None, description="Cron expression to update"
    )
    timezone: Optional[str] = Field(None, description="Timezone to update")
    enabled: Optional[bool] = Field(None, description="Enable/disable schedule")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: Optional[str]) -> Optional[str]:
        """Validate cron expression if provided."""
        if v is not None:
            try:
                croniter(v)
                return v
            except (ValueError, KeyError) as e:
                raise ValueError(f"Invalid cron expression: {v}") from e
        return v


class ScheduleRead(BaseModel):
    """Schema for reading a workflow schedule."""

    id: UUID
    workflow_id: UUID
    cron_expression: str
    timezone: str
    enabled: bool
    next_run: Optional[str] = None
    last_run: Optional[str] = None

    class Config:
        from_attributes = True
