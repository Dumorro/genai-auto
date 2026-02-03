"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client."""
    from src.api.main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Health check endpoint tests."""

    def test_root_endpoint(self, client):
        """Test root endpoint returns correct info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "GenAI Auto API"
        assert data["version"] == "1.0.0"
        assert "features" in data

    def test_health_endpoint(self, client):
        """Test health check endpoint."""
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestAuthEndpoints:
    """Authentication endpoint tests."""

    def test_register_missing_fields(self, client):
        """Test registration with missing fields."""
        response = client.post(
            "/api/v1/auth/register",
            json={"email": "test@example.com"}
        )
        assert response.status_code == 422

    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials."""
        response = client.post(
            "/api/v1/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "wrongpassword"
            }
        )
        assert response.status_code == 401

    def test_protected_endpoint_no_token(self, client):
        """Test accessing protected endpoint without token."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401


class TestDocumentEndpoints:
    """Document/RAG endpoint tests."""

    def test_search_documents(self, client):
        """Test document search endpoint."""
        response = client.post(
            "/api/v1/documents/search",
            json={
                "query": "engine specifications",
                "top_k": 5
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "results" in data
        assert "query" in data

    def test_get_stats(self, client):
        """Test knowledge base stats endpoint."""
        response = client.get("/api/v1/documents/stats")
        assert response.status_code == 200
        data = response.json()
        assert "total_chunks" in data

    def test_upload_no_auth(self, client):
        """Test document upload without authentication."""
        response = client.post(
            "/api/v1/documents/upload",
            files={"file": ("test.txt", b"test content", "text/plain")}
        )
        assert response.status_code == 401


class TestMetricsEndpoints:
    """Metrics endpoint tests."""

    def test_public_metrics(self, client):
        """Test public metrics endpoint."""
        response = client.get("/api/v1/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "requests_total" in data
