"""
Workflow schedule model.
Supports cron-based scheduling for periodic workflow execution.
"""

from datetime import datetime
from uuid import UUID, uuid4

from croniter import croniter
from sqlmodel import Field, SQLModel


class WorkflowSchedule(SQLModel, table=True):
    """
    Schedule configuration for periodic workflow execution.
    Uses cron expressions for flexible scheduling.
    """

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", unique=True)
    cron_expression: str = Field(
        index=True, description="Cron expression (e.g., '0 2 * * *')"
    )
    timezone: str = Field(default="UTC", description="Timezone for schedule")
    enabled: bool = Field(default=True, index=True, description="Schedule enabled")
    next_run: datetime | None = Field(
        default=None, index=True, description="Next scheduled run time"
    )
    last_run: datetime | None = Field(
        default=None, description="Last execution time"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def calculate_next_run(self, base_time: datetime | None = None) -> datetime:
        """
        Calculate the next run time based on cron expression.

        Args:
            base_time: Base time for calculation (defaults to now)

        Returns:
            Next scheduled run time
        """
        if base_time is None:
            base_time = datetime.utcnow()

        cron = croniter(self.cron_expression, base_time)
        return cron.get_next(datetime)

    def update_next_run(self) -> None:
        """Update next_run to the next scheduled time."""
        self.next_run = self.calculate_next_run()
        self.updated_at = datetime.utcnow()

    @staticmethod
    def validate_cron_expression(expression: str) -> bool:
        """
        Validate a cron expression.

        Args:
            expression: Cron expression to validate

        Returns:
            True if valid, False otherwise
        """
        try:
            croniter(expression)
            return True
        except (ValueError, KeyError):
            return False
