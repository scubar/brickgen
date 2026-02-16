"""Integration tests for authentication API routes."""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app
from backend.config import settings


@pytest.mark.asyncio
class TestAuthRoutes:
    """Tests for authentication API endpoints."""

    async def test_login_success(self):
        """Test successful login with valid credentials."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/login",
                json={
                    "username": settings.auth_username,
                    "password": settings.auth_password,
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert data["token_type"] == "bearer"
            assert len(data["access_token"]) > 0

    async def test_login_invalid_username(self):
        """Test login with invalid username."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/login",
                json={
                    "username": "wrong_user",
                    "password": settings.auth_password,
                }
            )
            
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data
            assert "Incorrect username or password" in data["detail"]

    async def test_login_invalid_password(self):
        """Test login with invalid password."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/login",
                json={
                    "username": settings.auth_username,
                    "password": "wrong_password",
                }
            )
            
            assert response.status_code == 401
            data = response.json()
            assert "detail" in data

    async def test_login_missing_fields(self):
        """Test login with missing required fields."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/login", json={})
            
            assert response.status_code == 422  # Validation error

    async def test_verify_token_valid(self):
        """Test token verification with valid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First, login to get a token
            login_response = await client.post(
                "/api/login",
                json={
                    "username": settings.auth_username,
                    "password": settings.auth_password,
                }
            )
            token = login_response.json()["access_token"]
            
            # Then verify the token
            verify_response = await client.get(
                "/api/verify",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            assert verify_response.status_code == 200
            data = verify_response.json()
            assert data["username"] == settings.auth_username
            assert data["authenticated"] is True

    async def test_verify_token_missing(self):
        """Test token verification without token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/verify")
            
            assert response.status_code == 401  # Unauthorized (no credentials)

    async def test_verify_token_invalid(self):
        """Test token verification with invalid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/api/verify",
                headers={"Authorization": "Bearer invalid.token.here"}
            )
            
            assert response.status_code == 401

    async def test_protected_route_without_token(self):
        """Test that protected routes require authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Try to access a protected route without token
            response = await client.get("/api/search?query=test")
            
            assert response.status_code == 401  # Unauthorized

    async def test_protected_route_with_valid_token(self):
        """Test that protected routes work with valid token."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # First, login to get a token
            login_response = await client.post(
                "/api/login",
                json={
                    "username": settings.auth_username,
                    "password": settings.auth_password,
                }
            )
            token = login_response.json()["access_token"]
            
            # Note: This test may fail if REBRICKABLE_API_KEY is not set,
            # but the authentication should pass through
            response = await client.get(
                "/api/search?query=test",
                headers={"Authorization": f"Bearer {token}"}
            )
            
            # Should not be 401 (authentication passed)
            # Could be 500 if no API key is configured, but auth passed
            assert response.status_code != 401
