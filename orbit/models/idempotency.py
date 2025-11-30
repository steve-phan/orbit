"""
Task idempotency models and utilities.
Prevents duplicate task executions and enables result caching.
"""

from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, Index, Text
from sqlmodel import Field, SQLModel


class IdempotencyKey(SQLModel, table=True):
    """
    Stores idempotency keys for task executions.
    Prevents duplicate task executions and caches results.
    """

    __tablename__ = "idempotencykey"
    __table_args__ = (
        Index("ix_idempotency_key_workflow_task", "workflow_id", "task_name", "key"),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    workflow_id: UUID = Field(foreign_key="workflow.id", index=True)
    task_name: str = Field(index=True)
    key: str = Field(index=True, description="Idempotency key")

    # Execution details
    status: str = Field(default="processing", index=True)  # processing, completed, failed
    result: dict[str, Any] | None = Field(default=None, sa_column=Column(JSON))
    error_message: str | None = Field(default=None, sa_column=Column(Text))

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    completed_at: datetime | None = Field(default=None)
    expires_at: datetime | None = Field(default=None, index=True)

    # Metadata
    request_hash: str | None = Field(default=None, description="Hash of request payload")
    execution_id: UUID | None = Field(default=None, description="Original execution ID")

    def is_expired(self) -> bool:
        """Check if idempotency key has expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def set_ttl(self, hours: int = 24):
        """Set time-to-live for idempotency key."""
        self.expires_at = datetime.utcnow() + timedelta(hours=hours)
