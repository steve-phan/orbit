"""
Authentication endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel.ext.asyncio.session import AsyncSession

from orbit.core.dependencies import get_auth_service, get_user_repository
from orbit.core.exceptions import AuthenticationError
from orbit.core.logging import get_logger
from orbit.db.session import get_session
from orbit.repositories.user_repository import UserRepository
from orbit.schemas.auth import Token, UserCreate, UserLogin, UserRead
from orbit.services.auth_service import AuthService

logger = get_logger("api.auth")
router = APIRouter()


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: UserCreate,
    session: AsyncSession = Depends(get_session),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """Register a new user."""
    try:
        service = get_auth_service(user_repo)
        user = await service.register_user(user_in)
        return user
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.message,
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/token", response_model=Token)
async def login_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """OAuth2 compatible token login, get an access token for future requests."""
    try:
        service = get_auth_service(user_repo)
        user_login = UserLogin(username=form_data.username, password=form_data.password)
        user = await service.authenticate_user(user_login)
        return await service.create_tokens(user)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/login", response_model=Token)
async def login(
    user_in: UserLogin,
    session: AsyncSession = Depends(get_session),
    user_repo: UserRepository = Depends(get_user_repository),
):
    """JSON login, get an access token for future requests."""
    try:
        service = get_auth_service(user_repo)
        user = await service.authenticate_user(user_in)
        return await service.create_tokens(user)
    except AuthenticationError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception as e:
        logger.error(f"Login failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )
