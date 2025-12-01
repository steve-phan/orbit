"""
Tests for authentication and authorization.
"""

import pytest
from orbit.core.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_api_key,
    verify_api_key,
    check_permissions,
    check_scopes,
)


def test_password_hashing():
    """Test password hashing and verification."""
    password = "mysecretpassword123"
    
    # Hash password
    hashed = get_password_hash(password)
    
    # Verify correct password
    assert verify_password(password, hashed) is True
    
    # Verify incorrect password
    assert verify_password("wrongpassword", hashed) is False


def test_password_hash_uniqueness():
    """Test that same password produces different hashes."""
    password = "samepassword"
    
    hash1 = get_password_hash(password)
    hash2 = get_password_hash(password)
    
    # Hashes should be different (bcrypt uses random salt)
    assert hash1 != hash2
    
    # But both should verify correctly
    assert verify_password(password, hash1) is True
    assert verify_password(password, hash2) is True


def test_create_access_token():
    """Test JWT access token creation."""
    data = {"sub": "user@example.com", "user_id": "123"}
    
    token = create_access_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 0


def test_create_refresh_token():
    """Test JWT refresh token creation."""
    data = {"sub": "user@example.com"}
    
    token = create_refresh_token(data)
    
    assert isinstance(token, str)
    assert len(token) > 0


def test_decode_token():
    """Test JWT token decoding."""
    data = {"sub": "user@example.com", "user_id": "123"}
    
    token = create_access_token(data)
    decoded = decode_token(token)
    
    assert decoded is not None
    assert decoded["sub"] == "user@example.com"
    assert decoded["user_id"] == "123"
    assert decoded["type"] == "access"
    assert "exp" in decoded


def test_decode_invalid_token():
    """Test decoding invalid token."""
    invalid_token = "invalid.token.here"
    
    decoded = decode_token(invalid_token)
    
    assert decoded is None


def test_token_types():
    """Test access and refresh token types."""
    data = {"sub": "user@example.com"}
    
    access_token = create_access_token(data)
    refresh_token = create_refresh_token(data)
    
    access_decoded = decode_token(access_token)
    refresh_decoded = decode_token(refresh_token)
    
    assert access_decoded["type"] == "access"
    assert refresh_decoded["type"] == "refresh"


def test_generate_api_key():
    """Test API key generation."""
    key, key_hash = generate_api_key()
    
    assert isinstance(key, str)
    assert isinstance(key_hash, str)
    assert len(key) > 0
    assert len(key_hash) > 0
    assert key != key_hash  # Key and hash should be different


def test_verify_api_key():
    """Test API key verification."""
    key, key_hash = generate_api_key()
    
    # Correct key should verify
    assert verify_api_key(key, key_hash) is True
    
    # Wrong key should not verify
    assert verify_api_key("wrongkey", key_hash) is False


def test_check_permissions_admin():
    """Test admin has all permissions."""
    user_roles = ["admin"]
    required_roles = ["editor", "viewer"]
    
    assert check_permissions(user_roles, required_roles) is True


def test_check_permissions_matching():
    """Test matching permissions."""
    user_roles = ["editor", "viewer"]
    required_roles = ["editor"]
    
    assert check_permissions(user_roles, required_roles) is True


def test_check_permissions_no_match():
    """Test no matching permissions."""
    user_roles = ["viewer"]
    required_roles = ["editor", "admin"]
    
    assert check_permissions(user_roles, required_roles) is False


def test_check_scopes_wildcard():
    """Test wildcard scope."""
    user_scopes = ["*"]
    required_scopes = ["read:workflows", "write:workflows"]
    
    assert check_scopes(user_scopes, required_scopes) is True


def test_check_scopes_matching():
    """Test matching scopes."""
    user_scopes = ["read:workflows", "write:workflows", "read:tasks"]
    required_scopes = ["read:workflows", "write:workflows"]
    
    assert check_scopes(user_scopes, required_scopes) is True


def test_check_scopes_partial_match():
    """Test partial scope match (should fail)."""
    user_scopes = ["read:workflows"]
    required_scopes = ["read:workflows", "write:workflows"]
    
    # User needs ALL required scopes
    assert check_scopes(user_scopes, required_scopes) is False
