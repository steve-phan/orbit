"""
Rate limiting middleware and utilities.
Protects API endpoints from abuse and ensures fair resource usage.
"""

import time

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

from orbit.core.logging import get_logger

logger = get_logger("core.rate_limit")


class TokenBucket:
    """
    Token bucket algorithm for rate limiting.
    Allows bursts while maintaining average rate.
    """

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize token bucket.

        Args:
            capacity: Maximum number of tokens
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self.tokens = capacity
        self.last_refill = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens.

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens consumed, False if not enough tokens
        """
        self._refill()

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False

    def _refill(self):
        """Refill tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now

    def get_wait_time(self, tokens: int = 1) -> float:
        """
        Get time to wait until tokens available.

        Args:
            tokens: Number of tokens needed

        Returns:
            Seconds to wait
        """
        self._refill()
        if self.tokens >= tokens:
            return 0

        tokens_needed = tokens - self.tokens
        return tokens_needed / self.refill_rate


class RateLimiter:
    """
    Rate limiter using token bucket algorithm.
    Supports per-IP and per-endpoint rate limiting.
    """

    def __init__(
        self,
        requests_per_minute: int = 60,
        burst_size: int | None = None,
    ):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Average requests allowed per minute
            burst_size: Maximum burst size (defaults to requests_per_minute)
        """
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size or requests_per_minute
        self.refill_rate = requests_per_minute / 60.0  # Tokens per second

        # Store token buckets per client
        self.buckets: dict[str, TokenBucket] = {}

        # Cleanup old buckets periodically
        self.last_cleanup = time.time()
        self.cleanup_interval = 300  # 5 minutes

    def is_allowed(self, client_id: str) -> bool:
        """
        Check if request is allowed for client.

        Args:
            client_id: Client identifier (e.g., IP address)

        Returns:
            True if allowed, False if rate limited
        """
        self._cleanup_old_buckets()

        # Get or create bucket for client
        if client_id not in self.buckets:
            self.buckets[client_id] = TokenBucket(
                capacity=self.burst_size, refill_rate=self.refill_rate
            )

        bucket = self.buckets[client_id]
        return bucket.consume(1)

    def get_wait_time(self, client_id: str) -> float:
        """
        Get time client needs to wait.

        Args:
            client_id: Client identifier

        Returns:
            Seconds to wait
        """
        if client_id not in self.buckets:
            return 0

        return self.buckets[client_id].get_wait_time(1)

    def _cleanup_old_buckets(self):
        """Remove old, unused buckets to prevent memory leak."""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        # Remove buckets that are full (haven't been used recently)
        to_remove = []
        for client_id, bucket in self.buckets.items():
            if bucket.tokens >= bucket.capacity:
                to_remove.append(client_id)

        for client_id in to_remove:
            del self.buckets[client_id]

        self.last_cleanup = now
        if to_remove:
            logger.debug(f"Cleaned up {len(to_remove)} old rate limit buckets")


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware for rate limiting HTTP requests.
    """

    def __init__(
        self,
        app,
        requests_per_minute: int = 60,
        burst_size: int | None = None,
        exclude_paths: list | None = None,
    ):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            requests_per_minute: Requests allowed per minute
            burst_size: Maximum burst size
            exclude_paths: Paths to exclude from rate limiting
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_minute, burst_size)
        self.exclude_paths = exclude_paths or ["/health", "/metrics"]

    async def dispatch(self, request: Request, call_next):
        """Process request with rate limiting."""
        # Skip rate limiting for excluded paths
        if any(request.url.path.startswith(path) for path in self.exclude_paths):
            return await call_next(request)

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            wait_time = self.rate_limiter.get_wait_time(client_ip)

            logger.warning(
                f"Rate limit exceeded for {client_ip} on {request.url.path}"
            )

            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded. Try again in {wait_time:.1f} seconds.",
                headers={"Retry-After": str(int(wait_time) + 1)},
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(
            self.rate_limiter.requests_per_minute
        )
        response.headers["X-RateLimit-Remaining"] = str(
            int(self.rate_limiter.buckets.get(client_ip, TokenBucket(0, 0)).tokens)
        )

        return response


# Global rate limiter instance
default_rate_limiter = RateLimiter(requests_per_minute=60, burst_size=100)
