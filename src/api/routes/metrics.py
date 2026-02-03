"""Metrics and observability endpoints."""

from fastapi import APIRouter, Depends

from src.api.auth import get_current_user, KeycloakUser, require_role
from src.api.observability import metrics
from src.api.cache import token_tracker

router = APIRouter()


@router.get("/metrics")
async def get_metrics():
    """Get system metrics (public summary)."""
    return {
        "status": "healthy",
        "requests_total": metrics.request_count,
        "cache_hit_rate": (
            metrics.cache_hits / (metrics.cache_hits + metrics.cache_misses)
            if (metrics.cache_hits + metrics.cache_misses) > 0
            else 0
        ),
    }


@router.get("/metrics/detailed")
async def get_detailed_metrics(
    user: KeycloakUser = Depends(require_role("admin")),
):
    """Get detailed system metrics (admin only)."""
    return metrics.get_metrics()


@router.get("/metrics/tokens")
async def get_token_usage(
    date: str = None,
    user: KeycloakUser = Depends(require_role("admin")),
):
    """Get token usage statistics (admin only)."""
    daily_usage = await token_tracker.get_daily_usage(date)
    return {
        "date": date or "today",
        "usage": daily_usage,
    }


@router.get("/metrics/tokens/session/{session_id}")
async def get_session_token_usage(
    session_id: str,
    user: KeycloakUser = Depends(get_current_user),
):
    """Get token usage for a specific session."""
    usage = await token_tracker.get_session_usage(session_id)
    return {
        "session_id": session_id,
        "usage": usage,
    }
