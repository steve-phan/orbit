"""
Tests for retry policy functionality.
"""

import pytest
from orbit.models.retry_policy import RetryPolicy


def test_retry_policy_defaults():
    """Test default retry policy."""
    policy = RetryPolicy()
    assert policy.max_retries == 0
    assert policy.initial_delay == 1.0
    assert policy.max_delay == 60.0
    assert policy.backoff_multiplier == 2.0
    assert policy.jitter is True


def test_retry_policy_should_retry():
    """Test retry decision logic."""
    policy = RetryPolicy(max_retries=3)
    
    assert policy.should_retry(0) is True
    assert policy.should_retry(1) is True
    assert policy.should_retry(2) is True
    assert policy.should_retry(3) is False
    assert policy.should_retry(4) is False


def test_retry_policy_calculate_delay():
    """Test exponential backoff calculation."""
    policy = RetryPolicy(
        max_retries=5,
        initial_delay=1.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
        jitter=False  # Disable jitter for predictable testing
    )
    
    # Attempt 0: 1.0 * (2^0) = 1.0
    assert policy.calculate_delay(0) == 1.0
    
    # Attempt 1: 1.0 * (2^1) = 2.0
    assert policy.calculate_delay(1) == 2.0
    
    # Attempt 2: 1.0 * (2^2) = 4.0
    assert policy.calculate_delay(2) == 4.0
    
    # Attempt 3: 1.0 * (2^3) = 8.0
    assert policy.calculate_delay(3) == 8.0
    
    # Attempt 4: 1.0 * (2^4) = 16.0
    assert policy.calculate_delay(4) == 16.0


def test_retry_policy_max_delay():
    """Test that delay is capped at max_delay."""
    policy = RetryPolicy(
        max_retries=10,
        initial_delay=1.0,
        max_delay=10.0,
        backoff_multiplier=2.0,
        jitter=False
    )
    
    # Attempt 5: 1.0 * (2^5) = 32.0, but capped at 10.0
    assert policy.calculate_delay(5) == 10.0


def test_retry_policy_with_jitter():
    """Test that jitter adds randomness to delay."""
    policy = RetryPolicy(
        max_retries=5,
        initial_delay=10.0,
        max_delay=60.0,
        backoff_multiplier=2.0,
        jitter=True
    )
    
    # Calculate delay multiple times
    delays = [policy.calculate_delay(0) for _ in range(100)]
    
    # All delays should be close to 10.0 but with variation
    assert all(7.5 <= d <= 12.5 for d in delays)  # ±25% jitter
    
    # Delays should not all be the same (randomness)
    assert len(set(delays)) > 1


def test_retry_policy_no_retries():
    """Test policy with no retries."""
    policy = RetryPolicy(max_retries=0)
    
    assert policy.should_retry(0) is False
    assert policy.calculate_delay(0) == 0
