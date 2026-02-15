"""Tests for authentication functionality."""
import pytest
from datetime import timedelta
from jose import jwt
from backend.auth import (
    create_access_token,
    verify_token,
    authenticate_user,
)
from backend.config import settings
from fastapi import HTTPException

class TestJWTTokens:
    """Tests for JWT token creation and verification."""

    def test_create_access_token(self):
        """Test creating a JWT access token."""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        # Token should be a string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Should be able to decode it
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_create_token_with_custom_expiry(self):
        """Test creating a token with custom expiration time."""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=30)
        token = create_access_token(data, expires_delta)
        
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "testuser"
        assert "exp" in payload

    def test_verify_valid_token(self):
        """Test verifying a valid JWT token."""
        data = {"sub": "testuser"}
        token = create_access_token(data)
        
        payload = verify_token(token)
        assert payload["sub"] == "testuser"

    def test_verify_invalid_token(self):
        """Test that invalid tokens raise HTTPException."""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(invalid_token)
        
        assert exc_info.value.status_code == 401
        assert "Invalid authentication credentials" in exc_info.value.detail

    def test_verify_token_without_sub(self):
        """Test that tokens without 'sub' claim raise HTTPException."""
        # Create token without 'sub'
        data = {"other": "data"}
        token = create_access_token(data)
        
        with pytest.raises(HTTPException) as exc_info:
            verify_token(token)
        
        assert exc_info.value.status_code == 401


class TestAuthenticateUser:
    """Tests for user authentication."""

    def test_authenticate_valid_user(self):
        """Test authentication with valid credentials."""
        # Use the configured username and password
        result = authenticate_user(settings.auth_username, settings.auth_password)
        assert result is True

    def test_authenticate_invalid_username(self):
        """Test authentication with invalid username."""
        result = authenticate_user("wrong_user", settings.auth_password)
        assert result is False

    def test_authenticate_invalid_password(self):
        """Test authentication with invalid password."""
        result = authenticate_user(settings.auth_username, "wrong_password")
        assert result is False

    def test_authenticate_both_invalid(self):
        """Test authentication with both username and password invalid."""
        result = authenticate_user("wrong_user", "wrong_password")
        assert result is False
