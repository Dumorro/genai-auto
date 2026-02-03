"""API endpoint tests."""

import pytest
from fastapi.testclient import TestClient


def test_root_endpoint():
    """Test root endpoint returns correct info."""
    # Import here to avoid loading all dependencies during collection
    from src.api.main import app

    client = TestClient(app)
    response = client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "GenAI Auto API"
    assert data["version"] == "1.0.0"


def test_health_endpoint():
    """Test health check endpoint."""
    from src.api.main import app

    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@pytest.mark.asyncio
async def test_orchestrator_classification():
    """Test intent classification."""
    from src.orchestrator.graph import Orchestrator, AgentState

    # This test requires API key, skip if not available
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    orchestrator = Orchestrator()

    # Test specs intent
    state: AgentState = {
        "messages": [{"role": "user", "content": "What is the towing capacity of my vehicle?"}],
        "session_id": "test-session",
        "customer_id": None,
        "vehicle_id": None,
        "metadata": {},
        "current_agent": None,
        "context": {},
    }

    result = await orchestrator.classify_intent(state)
    assert result["current_agent"] in ["specs", "maintenance", "troubleshoot"]


@pytest.mark.asyncio
async def test_maintenance_classification():
    """Test maintenance intent classification."""
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from src.orchestrator.graph import Orchestrator, AgentState

    orchestrator = Orchestrator()

    state: AgentState = {
        "messages": [{"role": "user", "content": "I need to schedule an oil change for next week"}],
        "session_id": "test-session",
        "customer_id": None,
        "vehicle_id": None,
        "metadata": {},
        "current_agent": None,
        "context": {},
    }

    result = await orchestrator.classify_intent(state)
    assert result["current_agent"] == "maintenance"


@pytest.mark.asyncio
async def test_troubleshoot_classification():
    """Test troubleshoot intent classification."""
    import os

    if not os.getenv("OPENAI_API_KEY"):
        pytest.skip("OPENAI_API_KEY not set")

    from src.orchestrator.graph import Orchestrator, AgentState

    orchestrator = Orchestrator()

    state: AgentState = {
        "messages": [{"role": "user", "content": "My check engine light is on and the car is making strange noises"}],
        "session_id": "test-session",
        "customer_id": None,
        "vehicle_id": None,
        "metadata": {},
        "current_agent": None,
        "context": {},
    }

    result = await orchestrator.classify_intent(state)
    assert result["current_agent"] == "troubleshoot"
