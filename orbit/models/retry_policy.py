"""
Retry policy models and utilities.
Implements exponential backoff with jitter for task retries.
"""

import random

from pydantic import BaseModel, Field


class RetryPolicy(BaseModel):
    """
    Retry policy configuration for tasks.

    Implements exponential backoff with optional jitter to prevent
    thundering herd problems.
    """

    max_retries: int = Field(default=0, ge=0, description="Maximum number of retry attempts")
    initial_delay: float = Field(default=1.0, gt=0, description="Initial delay in seconds")
    max_delay: float = Field(default=60.0, gt=0, description="Maximum delay in seconds")
    backoff_multiplier: float = Field(default=2.0, gt=1, description="Backoff multiplier")
    jitter: bool = Field(default=True, description="Add random jitter to delays")

    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt using exponential backoff.

        Args:
            attempt: The retry attempt number (0-indexed)

        Returns:
            Delay in seconds before next retry
        """
        if attempt >= self.max_retries:
            return 0

        # Calculate exponential backoff: initial_delay * (multiplier ^ attempt)
        delay = min(
            self.initial_delay * (self.backoff_multiplier ** attempt),
            self.max_delay
        )

        # Add jitter if enabled (±25% random variation)
        if self.jitter:
            jitter_range = delay * 0.25
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0, delay)

    def should_retry(self, attempt: int) -> bool:
        """
        Check if task should be retried.

        Args:
            attempt: Current retry attempt number (0-indexed)

        Returns:
            True if should retry, False otherwise
        """
        return attempt < self.max_retries


# Default retry policies for common scenarios
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_retries=0,
    initial_delay=1.0,
    max_delay=60.0,
    backoff_multiplier=2.0,
    jitter=True
)

AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_retries=5,
    initial_delay=0.5,
    max_delay=30.0,
    backoff_multiplier=2.0,
    jitter=True
)

CONSERVATIVE_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    initial_delay=2.0,
    max_delay=120.0,
    backoff_multiplier=3.0,
    jitter=True
)
