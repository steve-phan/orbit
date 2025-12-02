"""
Repository pattern for User and Auth data access.
"""

from uuid import UUID

from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.exceptions import DatabaseError, UserNotFoundError
from orbit.core.logging import get_logger
from orbit.models.auth import APIKey, User

logger = get_logger("repositories.user")


class UserRepository:
    """Repository for User entity operations."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(self, user: User) -> User:
        """Create a new user."""
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info(f"Created user: {user.username}")
            return user
        except IntegrityError:
            await self.session.rollback()
            raise DatabaseError("User with this email or username already exists")
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create user: {e}")
            raise DatabaseError(f"Failed to create user: {str(e)}")

    async def get_by_id(self, user_id: UUID) -> User:
        """Get user by ID."""
        try:
            query = select(User).where(User.id == user_id)
            result = await self.session.exec(query)
            user = result.first()

            if not user:
                raise UserNotFoundError(
                    f"User {user_id} not found",
                    details={"user_id": str(user_id)},
                )

            return user
        except UserNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get user {user_id}: {e}")
            raise DatabaseError(f"Failed to get user: {str(e)}")

    async def get_by_email(self, email: str) -> User | None:
        """Get user by email."""
        try:
            query = select(User).where(User.email == email)
            result = await self.session.exec(query)
            return result.first()
        except Exception as e:
            logger.error(f"Failed to get user by email {email}: {e}")
            raise DatabaseError(f"Failed to get user: {str(e)}")

    async def get_by_username(self, username: str) -> User | None:
        """Get user by username."""
        try:
            query = select(User).where(User.username == username)
            result = await self.session.exec(query)
            return result.first()
        except Exception as e:
            logger.error(f"Failed to get user by username {username}: {e}")
            raise DatabaseError(f"Failed to get user: {str(e)}")

    async def update(self, user: User) -> User:
        """Update an existing user."""
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info(f"Updated user: {user.id}")
            return user
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to update user {user.id}: {e}")
            raise DatabaseError(f"Failed to update user: {str(e)}")

    async def create_api_key(self, api_key: APIKey) -> APIKey:
        """Create a new API key."""
        try:
            self.session.add(api_key)
            await self.session.commit()
            await self.session.refresh(api_key)
            logger.info(f"Created API key for user: {api_key.user_id}")
            return api_key
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Failed to create API key: {e}")
            raise DatabaseError(f"Failed to create API key: {str(e)}")

    async def get_api_key_by_hash(self, key_hash: str) -> APIKey | None:
        """Get API key by hash."""
        try:
            query = select(APIKey).where(APIKey.key_hash == key_hash)
            result = await self.session.exec(query)
            return result.first()
        except Exception as e:
            logger.error(f"Failed to get API key: {e}")
            raise DatabaseError(f"Failed to get API key: {str(e)}")
