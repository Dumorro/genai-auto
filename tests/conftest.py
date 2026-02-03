"""Pytest configuration and fixtures."""

import os
import pytest

# Set test environment variables before importing app
os.environ["TESTING"] = "true"
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing"
os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test_db"
os.environ["REDIS_URL"] = "redis://localhost:6379"
os.environ["OPENROUTER_API_KEY"] = "test-api-key"
os.environ["CACHE_ENABLED"] = "false"


@pytest.fixture(scope="session")
def anyio_backend():
    """Use asyncio backend for async tests."""
    return "asyncio"


@pytest.fixture
def sample_document():
    """Sample document content for testing."""
    return """
# GenAuto X1 Specifications

## Engine
- Type: 2.0L Turbocharged
- Power: 250 hp
- Torque: 280 lb-ft

## Transmission
- 6-speed automatic
- Manual mode available

## Dimensions
- Length: 185 inches
- Width: 73 inches
- Height: 57 inches
- Wheelbase: 110 inches

## Safety Features
- 6 airbags
- ABS braking
- Electronic stability control
- Blind spot monitoring
"""


@pytest.fixture
def sample_user_data():
    """Sample user data for auth testing."""
    return {
        "email": "test@example.com",
        "password": "securepassword123",
        "name": "Test User",
    }


@pytest.fixture
def auth_headers(sample_user_data):
    """Generate auth headers with a test token."""
    from src.api.auth.jwt_auth import create_tokens
    
    tokens = create_tokens(
        user_id="test-user-id",
        email=sample_user_data["email"],
        name=sample_user_data["name"],
    )
    
    return {"Authorization": f"Bearer {tokens.access_token}"}
