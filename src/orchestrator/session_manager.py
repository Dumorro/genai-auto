"""
Session manager with task completion tracking.
"""

import time
from typing import Dict, Optional
from enum import Enum
from ..api.metrics import track_task_completion, track_human_handoff


class TaskStatus(Enum):
    """Task completion status."""
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ESCALATED = "escalated"


class HandoffReason(Enum):
    """Reason for human handoff."""
    LOW_CONFIDENCE = "low_confidence"
    USER_REQUEST = "user_request"
    SAFETY = "safety"
    ERROR = "error"


class ChatSession:
    """
    Chat session with automatic task completion tracking.
    """
    
    def __init__(
        self,
        session_id: str,
        agent: str,
        user_id: Optional[str] = None
    ):
        self.session_id = session_id
        self.agent = agent
        self.user_id = user_id
        self.start_time = time.time()
        self.status = "active"
        self.messages = []
        self.handoff_triggered = False
    
    def add_message(self, role: str, content: str, confidence: Optional[float] = None):
        """
        Add message to session.
        
        Args:
            role: 'user' or 'assistant'
            content: Message content
            confidence: Confidence score (for assistant messages)
        """
        self.messages.append({
            "role": role,
            "content": content,
            "confidence": confidence,
            "timestamp": time.time()
        })
    
    def check_abandonment(self, timeout_seconds: int = 300) -> bool:
        """
        Check if session appears abandoned.
        
        Args:
            timeout_seconds: Time threshold for abandonment (default 5 min)
        
        Returns:
            True if session is likely abandoned
        """
        if not self.messages:
            return False
        
        last_message_time = self.messages[-1]["timestamp"]
        time_since_last = time.time() - last_message_time
        
        return time_since_last > timeout_seconds
    
    def check_low_confidence(self, threshold: float = 0.7) -> bool:
        """
        Check if recent responses have low confidence.
        
        Args:
            threshold: Confidence threshold
        
        Returns:
            True if recent response is below threshold
        """
        if not self.messages:
            return False
        
        # Check last assistant message
        for msg in reversed(self.messages):
            if msg["role"] == "assistant" and msg["confidence"] is not None:
                return msg["confidence"] < threshold
        
        return False
    
    def trigger_handoff(
        self,
        reason: HandoffReason,
        confidence_score: Optional[float] = None
    ):
        """
        Trigger handoff to human support.
        
        Args:
            reason: Reason for handoff
            confidence_score: Current confidence score (if applicable)
        """
        self.handoff_triggered = True
        
        track_human_handoff(
            reason=reason.value,
            agent=self.agent,
            confidence_score=confidence_score
        )
    
    def complete(self, status: TaskStatus):
        """
        Mark session as complete and track metrics.
        
        Args:
            status: Completion status
        """
        if self.status != "active":
            return  # Already completed
        
        duration = time.time() - self.start_time
        
        track_task_completion(
            status=status.value,
            agent=self.agent,
            duration_seconds=duration
        )
        
        self.status = status.value
    
    def complete_successfully(self):
        """Mark task as successfully completed."""
        self.complete(TaskStatus.COMPLETED)
    
    def mark_abandoned(self):
        """Mark task as abandoned by user."""
        self.complete(TaskStatus.ABANDONED)
    
    def mark_escalated(self):
        """Mark task as escalated to human."""
        self.complete(TaskStatus.ESCALATED)


class SessionManager:
    """
    Manages multiple chat sessions with automatic cleanup.
    """
    
    def __init__(self):
        self.sessions: Dict[str, ChatSession] = {}
    
    def create_session(
        self,
        session_id: str,
        agent: str,
        user_id: Optional[str] = None
    ) -> ChatSession:
        """
        Create new session.
        
        Args:
            session_id: Unique session identifier
            agent: Agent handling session
            user_id: Optional user identifier
        
        Returns:
            New ChatSession instance
        """
        session = ChatSession(session_id, agent, user_id)
        self.sessions[session_id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """Get existing session."""
        return self.sessions.get(session_id)
    
    def cleanup_abandoned_sessions(self, timeout_seconds: int = 600):
        """
        Mark abandoned sessions and cleanup.
        
        Args:
            timeout_seconds: Time threshold for abandonment (default 10 min)
        """
        abandoned = []
        
        for session_id, session in self.sessions.items():
            if session.status == "active" and session.check_abandonment(timeout_seconds):
                session.mark_abandoned()
                abandoned.append(session_id)
        
        # Remove abandoned sessions
        for session_id in abandoned:
            del self.sessions[session_id]


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
from orchestrator.session_manager import SessionManager, TaskStatus, HandoffReason

# Initialize manager
session_manager = SessionManager()

# Create session
session = session_manager.create_session(
    session_id="sess_123",
    agent="specs",
    user_id="user_456"
)

# Track conversation
session.add_message("user", "How to change oil?")
session.add_message("assistant", "Follow these steps...", confidence=0.95)

# Check for low confidence
if session.check_low_confidence(threshold=0.7):
    session.trigger_handoff(
        reason=HandoffReason.LOW_CONFIDENCE,
        confidence_score=0.65
    )
    session.mark_escalated()
else:
    # User completed task
    session.complete_successfully()

# Metrics tracked automatically:
# - task_completion_total{status="completed", agent="specs"}
# - task_duration_seconds
# - human_handoff_total (if triggered)

# Periodic cleanup
session_manager.cleanup_abandoned_sessions(timeout_seconds=300)
"""
