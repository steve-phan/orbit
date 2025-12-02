import pytest
from httpx import AsyncClient

from orbit.core.config import settings


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration."""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "password123",
            "full_name": "Test User",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "test@example.com"
    assert data["username"] == "testuser"
    assert "id" in data
    assert "password" not in data


@pytest.mark.asyncio
async def test_login_user(client: AsyncClient):
    """Test user login."""
    # Register first
    await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "login@example.com",
            "username": "loginuser",
            "password": "password123",
        },
    )

    # Login
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "username": "loginuser",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Test login with wrong password."""
    # Register first
    await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "wrong@example.com",
            "username": "wronguser",
            "password": "password123",
        },
    )

    # Login with wrong password
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "username": "wronguser",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with nonexistent user."""
    response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "username": "nonexistent",
            "password": "password123",
        },
    )
    assert response.status_code == 401
