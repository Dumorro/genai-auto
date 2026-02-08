"""
Frontend integration tests.

Tests the frontend pages and WebSocket integration.
"""

import pytest
import httpx


BASE_URL = "http://localhost:8000"


@pytest.mark.integration
class TestFrontendIntegration:
    """Test frontend serving and integration."""
    
    @pytest.mark.asyncio
    async def test_home_page_accessible(self):
        """Test that home page is served correctly."""
        async with httpx.AsyncClient() as client:
            response = await client.get(BASE_URL)
            
            # Should return HTML
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            
            # Should contain expected content
            content = response.text
            assert "GenAI Auto" in content
            assert "How can I help you today?" in content
            assert "smart_toy" in content  # Icon
    
    @pytest.mark.asyncio
    async def test_chat_page_accessible(self):
        """Test that chat page is served correctly."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/chat")
            
            assert response.status_code == 200
            assert "text/html" in response.headers["content-type"]
            
            content = response.text
            assert "GenAI Auto Chat" in content
            assert "ws://localhost:8000/ws/chat" in content
            assert "WebSocket" in content
    
    @pytest.mark.asyncio
    async def test_chat_with_query_param(self):
        """Test chat page with initial query parameter."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/chat",
                params={"q": "Hello"}
            )
            
            assert response.status_code == 200
            # Page should load regardless of query param
            assert "GenAI Auto" in response.text
    
    @pytest.mark.asyncio
    async def test_static_files_routing(self):
        """Test that static file routing doesn't break API."""
        async with httpx.AsyncClient() as client:
            # API endpoints should still work
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            
            response = await client.get(f"{BASE_URL}/docs")
            assert response.status_code == 200
            
            response = await client.get(f"{BASE_URL}/api/v1/chat")
            # Should return error (no auth or bad request), but route should exist
            assert response.status_code in [400, 401, 422]
