"""
JWT authentication and authorization utilities.
"""

import secrets
from datetime import datetime, timedelta

from jose import JWTError, jwt
from passlib.context import CryptContext

from orbit.core.config import settings
from orbit.core.logging import get_logger

logger = get_logger("core.auth")

# Password hashing - using argon2 (modern, secure, no length limits)
pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")

# JWT settings
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def create_refresh_token(
    data: dict,
    expires_delta: timedelta | None = None,
) -> str:
    """
    Create JWT refresh token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return encoded_jwt


def decode_token(token: str) -> dict | None:
    """
    Decode and verify JWT token.

    Args:
        token: JWT token to decode

    Returns:
        Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[ALGORITHM],
        )
        return payload
    except JWTError as e:
        logger.warning(f"JWT decode error: {e}")
        return None


def generate_api_key() -> tuple[str, str]:
    """
    Generate a new API key.

    Returns:
        Tuple of (full_key, key_hash)
    """
    import hashlib

    # Generate random key (32 bytes = 64 hex chars)
    key = secrets.token_urlsafe(32)

    # Use SHA256 for API keys (bcrypt has 72-byte limit)
    key_hash = hashlib.sha256(key.encode()).hexdigest()

    return key, key_hash


def verify_api_key(plain_key: str, key_hash: str) -> bool:
    """Verify an API key against its hash."""
    import hashlib

    # Use SHA256 for API keys
    computed_hash = hashlib.sha256(plain_key.encode()).hexdigest()
    return secrets.compare_digest(computed_hash, key_hash)


def check_permissions(
    user_roles: list[str],
    required_roles: list[str],
) -> bool:
    """
    Check if user has required roles.

    Args:
        user_roles: User's roles
        required_roles: Required roles

    Returns:
        True if user has at least one required role
    """
    if "admin" in user_roles:
        return True

    return any(role in user_roles for role in required_roles)


def check_scopes(
    user_scopes: list[str],
    required_scopes: list[str],
) -> bool:
    """
    Check if user has required scopes.

    Args:
        user_scopes: User's scopes
        required_scopes: Required scopes

    Returns:
        True if user has all required scopes
    """
    if "*" in user_scopes:
        return True

    return all(scope in user_scopes for scope in required_scopes)
