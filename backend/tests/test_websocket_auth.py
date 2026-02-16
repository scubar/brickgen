"""Test WebSocket routes work without authentication blocking."""
import pytest
from httpx import AsyncClient, ASGITransport
from backend.main import app


@pytest.mark.asyncio
class TestWebSocketAuth:
    """Tests for WebSocket routes without auth blocking."""

    async def test_websocket_route_not_blocked_by_auth(self):
        """Test that WebSocket routes are not blocked by authentication."""
        # Note: This test verifies the WebSocket endpoint exists and is accessible
        # We can't easily test WebSocket connections with httpx, but we can verify
        # the route is registered and not blocked by auth middleware
        
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Try to connect to WebSocket route as HTTP (will fail but shouldn't be 401/403)
            # If auth was blocking it, we'd get 401 Unauthorized
            response = await client.get("/api/jobs/test-job-id/ws")
            
            # WebSocket upgrade will fail with HTTP client, but shouldn't be auth error
            # We expect 426 (Upgrade Required) or similar, not 401 (Unauthorized)
            assert response.status_code != 401, "WebSocket route should not be blocked by authentication"
            assert response.status_code != 403, "WebSocket route should not be blocked by authentication"


@pytest.mark.asyncio  
class TestProtectedRoutesStillRequireAuth:
    """Verify that HTTP routes still require authentication."""

    async def test_download_requires_auth(self):
        """Test download endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/download/test-job-id")
            assert response.status_code == 401, "Download route should require authentication"

    async def test_generate_requires_auth(self):
        """Test generate endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/api/generate",
                json={
                    "set_num": "10255-1",
                    "plate_width": 220,
                    "plate_depth": 220,
                    "plate_height": 250,
                    "generate_3mf": True,
                    "generate_stl": True
                }
            )
            assert response.status_code == 401, "Generate route should require authentication"

    async def test_search_requires_auth(self):
        """Test search endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/search?query=test")
            assert response.status_code == 401, "Search route should require authentication"

    async def test_settings_requires_auth(self):
        """Test settings endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/settings")
            assert response.status_code == 401, "Settings route should require authentication"

    async def test_projects_requires_auth(self):
        """Test projects endpoint requires authentication."""
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/projects")
            assert response.status_code == 401, "Projects route should require authentication"
