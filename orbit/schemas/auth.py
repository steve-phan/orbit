from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class Token(BaseModel):
    """Token response schema."""

    access_token: str
    refresh_token: str
    token_type: str


class TokenPayload(BaseModel):
    """Token payload schema."""

    sub: str | None = None
    type: str | None = None
    exp: datetime | None = None
    user_id: str | None = None


class UserBase(BaseModel):
    """Base User schema."""

    email: EmailStr
    username: str
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False
    roles: list[str] = Field(default_factory=list)


class UserCreate(UserBase):
    """User creation schema."""

    password: str


class UserUpdate(BaseModel):
    """User update schema."""

    email: EmailStr | None = None
    username: str | None = None
    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None
    roles: list[str] | None = None


class UserRead(UserBase):
    """User response schema."""

    id: UUID
    created_at: datetime
    updated_at: datetime
    last_login: datetime | None = None

    model_config = ConfigDict(from_attributes=True)


class UserLogin(BaseModel):
    """User login schema."""

    username: str
    password: str
