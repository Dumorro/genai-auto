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
            "falar com humano",
            "falar com atendente",
            "falar com pessoa",
            "atendimento humano",
            "speak to human",
            "talk to agent",
            "human support",
            "real person",
        ]
        if any(phrase in user_message.lower() for phrase in escalation_phrases):
            return True, EscalationReason.USER_REQUEST

        # Check for sensitive topics
        sensitive_keywords = [
            "acidente",
            "recall",
            "processo",
            "advogado",
            "lesão",
            "ferimento",
            "accident",
            "injury",
            "lawsuit",
            "legal",
        ]
        if any(keyword in user_message.lower() for keyword in sensitive_keywords):
            return True, EscalationReason.SENSITIVE_TOPIC

        # Check for safety concerns
        safety_keywords = [
            "freio não funciona",
            "brakes not working",
            "airbag",
            "vazamento combustível",
            "fuel leak",
            "fumaça",
            "smoke",
            "fogo",
            "fire",
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
                "Entendo que sua questão é complexa. Vou transferir você para um "
                "de nossos especialistas que poderá ajudá-lo melhor. Por favor, aguarde."
            ),
            EscalationReason.USER_REQUEST: (
                "Claro! Estou transferindo você para um atendente humano. "
                "Por favor, aguarde um momento."
            ),
            EscalationReason.SENSITIVE_TOPIC: (
                "Este assunto requer atenção especial de nossa equipe. "
                "Um especialista entrará em contato em breve."
            ),
            EscalationReason.COMPLEX_ISSUE: (
                "Sua situação precisa de uma análise mais detalhada. "
                "Estou conectando você com um técnico especializado."
            ),
            EscalationReason.REPEATED_FAILURE: (
                "Peço desculpas pela dificuldade. Vou transferi-lo para um "
                "atendente que poderá resolver seu problema diretamente."
            ),
            EscalationReason.SAFETY_CONCERN: (
                "⚠️ Questões de segurança são nossa prioridade. Um especialista "
                "entrará em contato imediatamente para ajudá-lo."
            ),
        }
        return messages.get(reason, "Transferindo para atendimento humano...")

    def get_handoff_response(self, escalation: EscalationResponse) -> str:
        """Format response to user about handoff."""
        response = escalation.message
        
        if escalation.estimated_wait_time:
            response += f"\n\nTempo estimado de espera: {escalation.estimated_wait_time} minutos."
        
        if escalation.agent_name:
            response += f"\n\nVocê será atendido por: {escalation.agent_name}"
        
        response += f"\n\nSeu número de protocolo: {escalation.escalation_id}"
        
        return response


# Global instance
handoff_manager = HumanHandoffManager()
