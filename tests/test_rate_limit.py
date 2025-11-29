"""
Tests for rate limiting functionality.
"""

import pytest
import time
from orbit.core.rate_limit import TokenBucket, RateLimiter


def test_token_bucket_initialization():
    """Test token bucket initialization."""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)
    assert bucket.capacity == 10
    assert bucket.tokens == 10
    assert bucket.refill_rate == 1.0


def test_token_bucket_consume():
    """Test consuming tokens."""
    bucket = TokenBucket(capacity=10, refill_rate=1.0)

    # Should be able to consume tokens
    assert bucket.consume(1) is True
    assert bucket.consume(5) is True

    # Should have 4 tokens left
    assert bucket.consume(4) is True

    # Should not be able to consume more
    assert bucket.consume(1) is False


def test_token_bucket_refill():
    """Test token refill over time."""
    bucket = TokenBucket(capacity=10, refill_rate=10.0)  # 10 tokens/second

    # Consume all tokens
    bucket.consume(10)
    assert bucket.consume(1) is False

    # Wait for refill
    time.sleep(0.2)  # Should add ~2 tokens

    # Should be able to consume again
    assert bucket.consume(1) is True


def test_token_bucket_max_capacity():
    """Test that tokens don't exceed capacity."""
    bucket = TokenBucket(capacity=5, refill_rate=10.0)

    # Wait for potential overfill
    time.sleep(1.0)

    # Should still be at capacity
    assert bucket.tokens <= bucket.capacity


def test_rate_limiter_basic():
    """Test basic rate limiter functionality."""
    limiter = RateLimiter(requests_per_minute=60, burst_size=10)

    # Should allow first request
    assert limiter.is_allowed("client1") is True

    # Should allow multiple requests up to burst
    for _ in range(9):
        assert limiter.is_allowed("client1") is True

    # Should block after burst
    assert limiter.is_allowed("client1") is False


def test_rate_limiter_multiple_clients():
    """Test rate limiter with multiple clients."""
    limiter = RateLimiter(requests_per_minute=60, burst_size=5)

    # Each client should have independent limits
    assert limiter.is_allowed("client1") is True
    assert limiter.is_allowed("client2") is True

    # Exhaust client1's tokens
    for _ in range(4):
        limiter.is_allowed("client1")

    # Client1 should be blocked
    assert limiter.is_allowed("client1") is False

    # Client2 should still be allowed
    assert limiter.is_allowed("client2") is True


def test_rate_limiter_refill():
    """Test rate limiter refills over time."""
    limiter = RateLimiter(requests_per_minute=60, burst_size=2)

    # Exhaust tokens
    limiter.is_allowed("client1")
    limiter.is_allowed("client1")
    assert limiter.is_allowed("client1") is False

    # Wait for refill (60 req/min = 1 req/sec)
    time.sleep(1.1)

    # Should be allowed again
    assert limiter.is_allowed("client1") is True


def test_rate_limiter_wait_time():
    """Test wait time calculation."""
    limiter = RateLimiter(requests_per_minute=60, burst_size=2)

    # Exhaust tokens
    limiter.is_allowed("client1")
    limiter.is_allowed("client1")

    # Should have wait time
    wait_time = limiter.get_wait_time("client1")
    assert wait_time > 0
    assert wait_time <= 1.0  # Should be less than 1 second for 1 token


def test_token_bucket_get_wait_time():
    """Test token bucket wait time calculation."""
    bucket = TokenBucket(capacity=10, refill_rate=2.0)  # 2 tokens/second

    # Consume all tokens
    bucket.consume(10)

    # Wait time for 1 token should be ~0.5 seconds
    wait_time = bucket.get_wait_time(1)
    assert 0.4 <= wait_time <= 0.6

    # Wait time for 4 tokens should be ~2 seconds
    wait_time = bucket.get_wait_time(4)
    assert 1.8 <= wait_time <= 2.2
