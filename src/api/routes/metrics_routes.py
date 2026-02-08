"""
Metrics and feedback routes for GenAI Auto
"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Literal
from ..metrics import get_metrics, track_user_feedback


router = APIRouter(prefix="/api/v1", tags=["metrics"])


# ============================================================================
# MODELS
# ============================================================================

class FeedbackRequest(BaseModel):
    message_id: str
    sentiment: Literal["positive", "negative"]
    comment: str | None = None


# ============================================================================
# ENDPOINTS
# ============================================================================

@router.get("/metrics")
async def metrics_endpoint():
    """
    Prometheus metrics endpoint for scraping.
    
    Returns:
        Prometheus-formatted metrics
    
    Example:
        curl http://localhost:8000/api/v1/metrics
    """
    return get_metrics()


@router.post("/feedback")
async def submit_feedback(feedback: FeedbackRequest):
    """
    Submit user feedback (thumbs up/down) for a message.
    
    Args:
        feedback: Feedback data (message_id, sentiment, optional comment)
    
    Returns:
        Success confirmation
    
    Example:
        curl -X POST http://localhost:8000/api/v1/feedback \
          -H "Content-Type: application/json" \
          -d '{
            "message_id": "msg_123",
            "sentiment": "positive",
            "comment": "Very helpful!"
          }'
    """
    # Track feedback in Prometheus
    track_user_feedback(
        message_id=feedback.message_id,
        sentiment=feedback.sentiment
    )
    
    # TODO: Store detailed feedback in database for analysis
    # await db.feedbacks.insert({
    #     'message_id': feedback.message_id,
    #     'sentiment': feedback.sentiment,
    #     'comment': feedback.comment,
    #     'timestamp': datetime.utcnow()
    # })
    
    return {
        "status": "success",
        "message": "Feedback recorded",
        "message_id": feedback.message_id,
        "sentiment": feedback.sentiment
    }


@router.get("/metrics/summary")
async def metrics_summary():
    """
    Human-readable metrics summary (for dashboards/UI).
    
    Returns:
        Summary of key metrics
    
    Example:
        curl http://localhost:8000/api/v1/metrics/summary
    """
    # TODO: Query Prometheus or cache to generate summary
    # For now, return placeholder
    return {
        "status": "ok",
        "message": "Use /metrics endpoint for Prometheus scraping, or set up Grafana dashboard",
        "endpoints": {
            "prometheus": "/api/v1/metrics",
            "feedback": "/api/v1/feedback"
        }
    }
