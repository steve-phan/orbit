"""
Tests for authentication middleware.
"""

import pytest
from httpx import AsyncClient

from orbit.core.config import settings


@pytest.mark.asyncio
async def test_get_current_user_without_token(client: AsyncClient):
    """Test accessing protected endpoint without token."""
    response = await client.get(f"{settings.API_V1_STR}/auth/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_invalid_token(client: AsyncClient):
    """Test accessing protected endpoint with invalid token."""
    response = await client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": "Bearer invalid_token"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_with_valid_token(client: AsyncClient):
    """Test accessing protected endpoint with valid token."""
    # Register user
    register_response = await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "protected@example.com",
            "username": "protecteduser",
            "password": "password123",
            "full_name": "Protected User",
        },
    )
    assert register_response.status_code == 201

    # Login
    login_response = await client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "username": "protecteduser",
            "password": "password123",
        },
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    access_token = token_data["access_token"]

    # Access protected endpoint
    me_response = await client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me_response.status_code == 200
    user_data = me_response.json()
    assert user_data["username"] == "protecteduser"
    assert user_data["email"] == "protected@example.com"


@pytest.mark.asyncio
async def test_oauth2_token_endpoint(client: AsyncClient):
    """Test OAuth2 compatible token endpoint."""
    # Register user
    await client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "oauth@example.com",
            "username": "oauthuser",
            "password": "password123",
        },
    )

    # Login using OAuth2 form
    response = await client.post(
        f"{settings.API_V1_STR}/auth/token",
        data={
            "username": "oauthuser",
            "password": "password123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
