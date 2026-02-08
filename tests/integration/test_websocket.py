"""
WebSocket Integration Tests

Tests real-time streaming chat functionality via WebSocket.
"""

import pytest
import asyncio
import json
from typing import List, Dict, Any

import httpx
from fastapi.testclient import TestClient


# Base URL for tests
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/ws/chat"

# Test user credentials
TEST_USER = {
    "email": "test_ws@genai.auto",
    "password": "TestWS123",
    "name": "WS Test User"
}


class TestWebSocketChat:
    """WebSocket chat integration tests."""
    
    access_token: str = None
    
    @pytest.mark.asyncio
    async def test_01_setup_user(self):
        """Setup test user for WebSocket tests."""
        async with httpx.AsyncClient() as client:
            # Try to register (may already exist)
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json=TEST_USER
            )
            
            # Login to get token
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "email": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                TestWebSocketChat.access_token = data["access_token"]
                assert TestWebSocketChat.access_token is not None
    
    def test_02_websocket_connect(self):
        """Test WebSocket connection without authentication."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Connection should succeed
            assert websocket is not None
    
    def test_03_websocket_auth_via_message(self):
        """Test WebSocket authentication via message."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        if not TestWebSocketChat.access_token:
            pytest.skip("No access token available")
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Send auth message
            websocket.send_json({
                "type": "auth",
                "token": TestWebSocketChat.access_token
            })
            
            # Receive auth response
            data = websocket.receive_json()
            assert data["type"] == "auth_success"
            assert "user" in data
    
    def test_04_websocket_auth_failure(self):
        """Test WebSocket authentication with invalid token."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Send invalid token
            websocket.send_json({
                "type": "auth",
                "token": "invalid_token_12345"
            })
            
            # Receive auth error
            data = websocket.receive_json()
            assert data["type"] == "auth_error"
    
    def test_05_websocket_message_without_auth(self):
        """Test sending message without authentication."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Try to send message without auth
            websocket.send_json({
                "type": "message",
                "message": "Hello"
            })
            
            # Should receive auth error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "AUTH_REQUIRED"
    
    def test_06_websocket_streaming_chat(self):
        """Test streaming chat with authentication."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        if not TestWebSocketChat.access_token:
            pytest.skip("No access token available")
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Authenticate
            websocket.send_json({
                "type": "auth",
                "token": TestWebSocketChat.access_token
            })
            
            # Wait for auth success
            auth_response = websocket.receive_json()
            assert auth_response["type"] == "auth_success"
            
            # Send chat message
            websocket.send_json({
                "type": "message",
                "message": "What is the engine power of GenAuto X1?",
                "session_id": "test-ws-session-1"
            })
            
            # Collect responses
            messages: List[Dict[str, Any]] = []
            tokens: List[str] = []
            
            while True:
                try:
                    data = websocket.receive_json(timeout=30)
                    messages.append(data)
                    
                    if data["type"] == "token":
                        tokens.append(data["token"])
                    
                    if data["type"] == "complete":
                        break
                    
                    if data["type"] == "error":
                        pytest.fail(f"Error received: {data['error']}")
                
                except Exception as e:
                    break
            
            # Verify response structure
            assert len(messages) > 0
            
            # Should have progress updates
            progress_messages = [m for m in messages if m["type"] == "progress"]
            assert len(progress_messages) > 0
            
            # Should have complete message
            complete_messages = [m for m in messages if m["type"] == "complete"]
            assert len(complete_messages) == 1
            
            complete = complete_messages[0]
            assert "response" in complete
            assert len(complete["response"]) > 0
            assert "metadata" in complete
    
    def test_07_websocket_empty_message(self):
        """Test sending empty message."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        if not TestWebSocketChat.access_token:
            pytest.skip("No access token available")
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Authenticate
            websocket.send_json({
                "type": "auth",
                "token": TestWebSocketChat.access_token
            })
            
            auth_response = websocket.receive_json()
            assert auth_response["type"] == "auth_success"
            
            # Send empty message
            websocket.send_json({
                "type": "message",
                "message": ""
            })
            
            # Should receive error
            data = websocket.receive_json()
            assert data["type"] == "error"
            assert data["code"] == "EMPTY_MESSAGE"
    
    def test_08_websocket_multiple_messages(self):
        """Test sending multiple messages in same connection."""
        from fastapi.testclient import TestClient
        from src.api.main import app
        
        if not TestWebSocketChat.access_token:
            pytest.skip("No access token available")
        
        client = TestClient(app)
        
        with client.websocket_connect("/ws/chat") as websocket:
            # Authenticate
            websocket.send_json({
                "type": "auth",
                "token": TestWebSocketChat.access_token
            })
            
            auth_response = websocket.receive_json()
            assert auth_response["type"] == "auth_success"
            
            # Send first message
            websocket.send_json({
                "type": "message",
                "message": "What is the engine?",
                "session_id": "test-ws-multi-1"
            })
            
            # Wait for complete response
            while True:
                data = websocket.receive_json(timeout=30)
                if data["type"] == "complete":
                    break
            
            # Send second message
            websocket.send_json({
                "type": "message",
                "message": "What fuel does it use?",
                "session_id": "test-ws-multi-1"
            })
            
            # Wait for second complete response
            messages_count = 0
            while True:
                data = websocket.receive_json(timeout=30)
                messages_count += 1
                if data["type"] == "complete":
                    assert "response" in data
                    break
                if messages_count > 100:  # Safety limit
                    break
            
            assert messages_count > 0
    
    def test_09_websocket_test_page_accessible(self):
        """Test that WebSocket test page is accessible."""
        import httpx
        
        response = httpx.get(f"{BASE_URL}/ws/test")
        assert response.status_code == 200
        assert "WebSocket Chat Test" in response.text
        assert "ws.onopen" in response.text  # Should contain WebSocket JS code


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
