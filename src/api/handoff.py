"""Human handoff module for escalation to human support."""

from typing import Optional
from datetime import datetime
from enum import Enum

import structlog
import httpx
from pydantic import BaseModel, Field

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class EscalationReason(str, Enum):
    """Reasons for escalating to human support."""

    LOW_CONFIDENCE = "low_confidence"
    USER_REQUEST = "user_request"
    SENSITIVE_TOPIC = "sensitive_topic"
    COMPLEX_ISSUE = "complex_issue"
    REPEATED_FAILURE = "repeated_failure"
    SAFETY_CONCERN = "safety_concern"


class EscalationRequest(BaseModel):
    """Request to escalate to human support."""

    session_id: str
    customer_id: Optional[str] = None
    reason: EscalationReason
    confidence_score: Optional[float] = None
    conversation_summary: str
    last_user_message: str
    metadata: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EscalationResponse(BaseModel):
    """Response from human handoff system."""

    escalation_id: str
    status: str  # queued, assigned, in_progress, resolved
    estimated_wait_time: Optional[int] = None  # minutes
    agent_name: Optional[str] = None
    message: str


class HumanHandoffManager:
    """Manages escalation to human support agents."""

    def __init__(self):
        self.confidence_threshold = settings.confidence_threshold
        self.webhook_url = settings.human_support_webhook

    def should_escalate(
        self,
        confidence_score: float,
        user_message: str,
        context: dict = None,
    ) -> tuple[bool, Optional[EscalationReason]]:
        """Determine if conversation should be escalated to human.
        
        Returns:
            Tuple of (should_escalate, reason)
        """
        # Check confidence threshold
        if confidence_score < self.confidence_threshold:
            return True, EscalationReason.LOW_CONFIDENCE

        # Check for explicit user request
        escalation_phrases = [
            "speak to human",
            "talk to agent",
            "human support",
            "real person",
            "talk to someone",
            "speak to someone",
            "customer service",
            "representative",
        ]
        if any(phrase in user_message.lower() for phrase in escalation_phrases):
            return True, EscalationReason.USER_REQUEST

        # Check for sensitive topics
        sensitive_keywords = [
            "accident",
            "injury",
            "lawsuit",
            "legal",
            "recall",
            "lawyer",
            "attorney",
            "sue",
            "compensation",
            "damage claim",
        ]
        if any(keyword in user_message.lower() for keyword in sensitive_keywords):
            return True, EscalationReason.SENSITIVE_TOPIC

        # Check for safety concerns
        safety_keywords = [
            "brakes not working",
            "brake failure",
            "airbag",
            "fuel leak",
            "gas leak",
            "smoke",
            "fire",
            "burning smell",
            "steering failure",
        ]
        if any(keyword in user_message.lower() for keyword in safety_keywords):
            return True, EscalationReason.SAFETY_CONCERN

        return False, None

    async def escalate(
        self,
        session_id: str,
        reason: EscalationReason,
        conversation_summary: str,
        last_user_message: str,
        confidence_score: float = None,
        customer_id: str = None,
        metadata: dict = None,
    ) -> EscalationResponse:
        """Escalate conversation to human support."""
        
        request = EscalationRequest(
            session_id=session_id,
            customer_id=customer_id,
            reason=reason,
            confidence_score=confidence_score,
            conversation_summary=conversation_summary,
            last_user_message=last_user_message,
            metadata=metadata or {},
        )

        logger.info(
            "Escalating to human support",
            session_id=session_id,
            reason=reason.value,
            confidence_score=confidence_score,
        )

        # Send to webhook if configured
        if self.webhook_url:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        self.webhook_url,
                        json=request.model_dump(mode="json"),
                        timeout=10.0,
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    return EscalationResponse(**data)

            except Exception as e:
                logger.error("Failed to send escalation webhook", error=str(e))

        # Return default response if webhook fails or not configured
        return EscalationResponse(
            escalation_id=f"ESC-{session_id[:8]}",
            status="queued",
            estimated_wait_time=5,
            message=self._get_escalation_message(reason),
        )

    def _get_escalation_message(self, reason: EscalationReason) -> str:
        """Get user-friendly escalation message."""
        messages = {
            EscalationReason.LOW_CONFIDENCE: (
                "I understand your question is complex. I'm transferring you to one "
                "of our specialists who can better assist you. Please hold."
            ),
            EscalationReason.USER_REQUEST: (
                "Of course! I'm connecting you to a human representative. "
                "Please wait a moment."
            ),
            EscalationReason.SENSITIVE_TOPIC: (
                "This matter requires special attention from our team. "
                "A specialist will contact you shortly."
            ),
            EscalationReason.COMPLEX_ISSUE: (
                "Your situation needs a more detailed analysis. "
                "I'm connecting you with a specialized technician."
            ),
            EscalationReason.REPEATED_FAILURE: (
                "I apologize for the difficulty. I'm transferring you to a "
                "representative who can resolve your issue directly."
            ),
            EscalationReason.SAFETY_CONCERN: (
                "⚠️ Safety concerns are our priority. A specialist "
                "will contact you immediately to assist."
            ),
        }
        return messages.get(reason, "Transferring to human support...")

    def get_handoff_response(self, escalation: EscalationResponse) -> str:
        """Format response to user about handoff."""
        response = escalation.message
        
        if escalation.estimated_wait_time:
            response += f"\n\nEstimated wait time: {escalation.estimated_wait_time} minutes."
        
        if escalation.agent_name:
            response += f"\n\nYou will be assisted by: {escalation.agent_name}"
        
        response += f"\n\nYour reference number: {escalation.escalation_id}"
        
        return response


# Global instance
handoff_manager = HumanHandoffManager()
