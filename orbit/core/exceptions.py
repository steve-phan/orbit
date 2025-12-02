"""
Custom exception hierarchy for Orbit.
Provides specific exceptions for different error scenarios.
"""


class OrbitException(Exception):
    """Base exception for all Orbit errors."""

    def __init__(self, message: str, details: dict = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class WorkflowNotFoundError(OrbitException):
    """Raised when a workflow is not found."""

    pass


class WorkflowValidationError(OrbitException):
    """Raised when workflow validation fails."""

    pass


class TaskExecutionError(OrbitException):
    """Raised when task execution fails."""

    pass


class DAGValidationError(OrbitException):
    """Raised when DAG validation fails (circular dependencies, etc)."""

    pass


class DatabaseError(OrbitException):
    """Raised when database operations fail."""

    pass


class ConfigurationError(OrbitException):
    """Raised when configuration is invalid."""

    pass


class UserNotFoundError(OrbitException):
    """Raised when a user is not found."""

    pass


class AuthenticationError(OrbitException):
    """Raised when authentication fails."""

    pass
