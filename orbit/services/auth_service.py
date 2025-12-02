"""
Authentication service layer.
Handles user authentication and token management.
"""

from datetime import timedelta

from orbit.core.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    verify_password,
)
from orbit.core.exceptions import AuthenticationError
from orbit.core.logging import get_logger
from orbit.models.auth import User
from orbit.repositories.user_repository import UserRepository
from orbit.schemas.auth import Token, UserCreate, UserLogin

logger = get_logger("services.auth")


class AuthService:
    """Service for authentication business logic."""

    def __init__(self, user_repo: UserRepository):
        self.user_repo = user_repo

    async def register_user(self, user_data: UserCreate) -> User:
        """Register a new user."""
        logger.info(f"Registering new user: {user_data.username}")

        # Check if user exists
        if await self.user_repo.get_by_email(user_data.email):
            raise AuthenticationError("Email already registered")
        if await self.user_repo.get_by_username(user_data.username):
            raise AuthenticationError("Username already taken")

        # Create user entity
        user = User(
            email=user_data.email,
            username=user_data.username,
            hashed_password=get_password_hash(user_data.password),
            full_name=user_data.full_name,
            is_active=user_data.is_active,
            is_superuser=user_data.is_superuser,
            roles=user_data.roles,
        )

        return await self.user_repo.create(user)

    async def authenticate_user(self, login_data: UserLogin) -> User:
        """Authenticate a user."""
        user = await self.user_repo.get_by_username(login_data.username)

        if not user:
            raise AuthenticationError("Incorrect username or password")

        if not verify_password(login_data.password, user.hashed_password):
            raise AuthenticationError("Incorrect username or password")

        if not user.is_active:
            raise AuthenticationError("User is inactive")

        return user

    async def create_tokens(self, user: User) -> Token:
        """Create access and refresh tokens for user."""
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.username, "user_id": str(user.id)},
            expires_delta=access_token_expires,
        )

        refresh_token = create_refresh_token(
            data={"sub": user.username, "user_id": str(user.id)}
        )

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
        )
