"""
Pydantic schemas for workflow schedules.
"""

from uuid import UUID

from croniter import croniter
from pydantic import BaseModel, Field, field_validator


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

    cron_expression: str | None = Field(
        None, description="Cron expression to update"
    )
    timezone: str | None = Field(None, description="Timezone to update")
    enabled: bool | None = Field(None, description="Enable/disable schedule")

    @field_validator("cron_expression")
    @classmethod
    def validate_cron(cls, v: str | None) -> str | None:
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
    next_run: str | None = None
    last_run: str | None = None

    class Config:
        from_attributes = True
