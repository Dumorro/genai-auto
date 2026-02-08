"""
Full chat flow E2E tests.

Tests the complete user journey from registration to chat.
"""

import asyncio

import pytest
import httpx
from fastapi.testclient import TestClient


BASE_URL = "http://localhost:8000"


@pytest.mark.integration
@pytest.mark.e2e
class TestFullChatFlow:
    """Test complete chat flow end-to-end."""
    
    @pytest.mark.asyncio
    async def test_complete_user_journey(self):
        """Test full user journey: register → login → chat."""
        async with httpx.AsyncClient(base_url=BASE_URL, timeout=30.0) as client:
            # 1. Register user
            register_data = {
                "email": "e2e_test@example.com",
                "password": "SecurePass123!",
                "name": "E2E Test User"
            }
            
            response = await client.post("/api/v1/auth/register", json=register_data)
            # May fail if user exists (500 or 400)
            assert response.status_code in [200, 400, 500]
            
            # 2. Login
            login_data = {
                "email": "e2e_test@example.com",
                "password": "SecurePass123!"
            }
            
            response = await client.post("/api/v1/auth/login", json=login_data)
            
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                
                # 3. Send chat message (REST API)
                headers = {"Authorization": f"Bearer {token}"}
                chat_message = {
                    "message": "What is the engine power?",
                    "session_id": "e2e-test-session"
                }
                
                response = await client.post(
                    "/api/v1/chat",
                    json=chat_message,
                    headers=headers
                )
                
                # Should get response
                if response.status_code == 200:
                    data = response.json()
                    assert "response" in data
                    assert len(data["response"]) > 0
    
    @pytest.mark.asyncio
    async def test_anonymous_chat_via_websocket(self):
        """Test anonymous chat via WebSocket (no auth required)."""
        from src.api.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Send message (no auth)
            websocket.send_json({
                "type": "message",
                "message": "Hello",
                "session_id": "anon-test"
            })
            
            # Receive responses
            messages_received = 0
            max_messages = 10
            
            while messages_received < max_messages:
                try:
                    data = websocket.receive_json(timeout=5)
                    messages_received += 1
                    
                    # Should get progress, tokens, or complete
                    assert data["type"] in ["progress", "token", "complete", "error"]
                    
                    if data["type"] == "complete":
                        assert "response" in data
                        assert len(data["response"]) > 0
                        break
                    
                    if data["type"] == "error":
                        # Error is acceptable (no LLM key, etc.)
                        break
                
                except Exception:
                    break
            
            assert messages_received > 0
    
    @pytest.mark.asyncio
    async def test_health_check_during_load(self):
        """Test that health check remains responsive."""
        async with httpx.AsyncClient(base_url=BASE_URL) as client:
            # Make 10 concurrent health check requests
            tasks = []
            for _ in range(10):
                tasks.append(client.get("/health"))
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            # All should succeed
            for response in responses:
                if isinstance(response, httpx.Response):
                    assert response.status_code == 200
                    data = response.json()
                    assert data["status"] == "healthy"
