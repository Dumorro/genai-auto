"""
E2E Integration Tests for GenAI Auto API

Tests the complete user flow:
1. User registration
2. Login
3. Document upload and search
4. Chat with RAG
5. Agent interactions
"""

import pytest
import httpx
import asyncio
from typing import  Any


# Base URL for tests
BASE_URL = "http://localhost:8000"

# Test user credentials (keep password short to avoid bcrypt 72-byte limit)
TEST_USER = {
    "email": "test_e2e@genai.auto",
    "password": "TestPass123",
    "name": "E2E Test User"
}


class TestE2EFlow:
    """End-to-end integration tests."""
    
    access_token: str = None
    refresh_token: str = None
    user_id: str = None
    
    @pytest.mark.asyncio
    async def test_01_health_check(self):
        """Test API health endpoint."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/health")
            assert response.status_code == 200
            assert response.json()["status"] == "healthy"
    
    @pytest.mark.asyncio
    async def test_02_user_registration(self):
        """Test user registration."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/register",
                json=TEST_USER
            )
            
            # Allow 200 (success) or 400 (user already exists)
            assert response.status_code in [200, 400]
            
            if response.status_code == 200:
                data = response.json()
                assert "access_token" in data
                assert "user" in data
                assert data["user"]["email"] == TEST_USER["email"]
                TestE2EFlow.access_token = data["access_token"]
                TestE2EFlow.refresh_token = data["refresh_token"]
                TestE2EFlow.user_id = data["user"]["id"]
    
    @pytest.mark.asyncio
    async def test_03_user_login(self):
        """Test user login."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/login",
                json={
                    "email": TEST_USER["email"],
                    "password": TEST_USER["password"]
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            assert "refresh_token" in data
            assert "user" in data
            
            # Store tokens for subsequent tests
            TestE2EFlow.access_token = data["access_token"]
            TestE2EFlow.refresh_token = data["refresh_token"]
            TestE2EFlow.user_id = data["user"]["id"]
    
    @pytest.mark.asyncio
    async def test_04_get_current_user(self):
        """Test getting current user info."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/auth/me",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == TEST_USER["email"]
            assert data["name"] == TEST_USER["name"]
    
    @pytest.mark.asyncio
    async def test_05_refresh_token(self):
        """Test token refresh."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/auth/refresh",
                json={"refresh_token": TestE2EFlow.refresh_token}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "access_token" in data
            
            # Update access token
            TestE2EFlow.access_token = data["access_token"]
    
    @pytest.mark.asyncio
    async def test_06_list_documents(self):
        """Test listing documents."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/documents/",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "documents" in data
            assert isinstance(data["documents"], list)
    
    @pytest.mark.asyncio
    async def test_07_search_documents(self):
        """Test semantic document search."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/documents/search",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "query": "engine specifications",
                    "top_k": 5
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "results" in data
            assert isinstance(data["results"], list)
            
            # Should have results from seeded data
            if len(data["results"]) > 0:
                result = data["results"][0]
                assert "content" in result
                assert "score" in result
                assert "metadata" in result
    
    @pytest.mark.asyncio
    async def test_08_chat_simple_query(self):
        """Test simple chat query."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/chat",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "message": "What is the engine power of GenAuto X1?",
                    "session_id": "test-e2e-session-1"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            assert "session_id" in data
            assert len(data["response"]) > 0
            
            # Response should mention power specs
            assert any(keyword in data["response"].lower() 
                      for keyword in ["hp", "power", "128", "116"])
    
    @pytest.mark.asyncio
    async def test_09_chat_with_context(self):
        """Test chat with conversation context."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            # First message
            response1 = await client.post(
                f"{BASE_URL}/api/v1/chat",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "message": "Tell me about the GenAuto X1 engine",
                    "session_id": "test-e2e-session-2"
                }
            )
            assert response1.status_code == 200
            
            # Follow-up message (should maintain context)
            response2 = await client.post(
                f"{BASE_URL}/api/v1/chat",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "message": "What fuel does it use?",
                    "session_id": "test-e2e-session-2"
                }
            )
            
            assert response2.status_code == 200
            data = response2.json()
            assert "response" in data
            
            # Should mention flex fuel
            assert any(keyword in data["response"].lower() 
                      for keyword in ["flex", "gasoline", "ethanol"])
    
    @pytest.mark.asyncio
    async def test_10_chat_maintenance_query(self):
        """Test maintenance-related chat."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/chat",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "message": "When should I change the oil?",
                    "session_id": "test-e2e-session-3"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            
            # Should mention maintenance intervals
            assert any(keyword in data["response"].lower() 
                      for keyword in ["oil", "km", "months", "service"])
    
    @pytest.mark.asyncio
    async def test_11_chat_troubleshooting(self):
        """Test troubleshooting query."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/chat",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "message": "My car won't start. What should I check?",
                    "session_id": "test-e2e-session-4"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            assert "response" in data
            
            # Should provide troubleshooting steps
            assert any(keyword in data["response"].lower() 
                      for keyword in ["battery", "check", "fuel", "starter"])
    
    @pytest.mark.asyncio
    async def test_12_chat_confidence_tracking(self):
        """Test that chat returns confidence score."""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{BASE_URL}/api/v1/chat",
                headers={"Authorization": f"Bearer {TestE2EFlow.access_token}"},
                json={
                    "message": "What are the safety features?",
                    "session_id": "test-e2e-session-5"
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Check if confidence is tracked
            if "metadata" in data:
                assert "confidence" in data["metadata"] or "agent" in data["metadata"]
    
    @pytest.mark.asyncio
    async def test_13_invalid_auth(self):
        """Test requests with invalid authentication."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/auth/me",
                headers={"Authorization": "Bearer invalid_token_12345"}
            )
            
            assert response.status_code == 401
    
    @pytest.mark.asyncio
    async def test_14_missing_auth(self):
        """Test requests without authentication."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{BASE_URL}/api/v1/auth/me"
            )
            
            assert response.status_code in [401, 403]
    
    @pytest.mark.asyncio
    async def test_15_api_docs_accessible(self):
        """Test that API documentation is accessible."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{BASE_URL}/docs")
            assert response.status_code == 200
            
            response = await client.get(f"{BASE_URL}/openapi.json")
            assert response.status_code == 200


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
