"""
Agent router with routing accuracy tracking.
"""

from typing import Tuple, Optional
from enum import Enum
from ..api.metrics import track_agent_routing, track_agent_rerouting


class AgentType(Enum):
    """Available agents."""
    SPECS = "specs"
    MAINTENANCE = "maintenance"
    TROUBLESHOOT = "troubleshoot"


class RoutingMethod(Enum):
    """Routing method used."""
    INTENT_CLASSIFICATION = "intent_classification"
    RULE_BASED = "rule_based"
    FALLBACK = "fallback"


class RerouteReason(Enum):
    """Reason for rerouting."""
    WRONG_AGENT = "wrong_agent"
    FALLBACK = "fallback"
    ESCALATION = "escalation"


class AgentRouter:
    """
    Routes messages to appropriate agent with metrics tracking.
    """
    
    def __init__(self, intent_classifier):
        self.intent_classifier = intent_classifier
        self.high_confidence_threshold = 0.8
        self.medium_confidence_threshold = 0.5
    
    async def route(self, message: str) -> Tuple[AgentType, float]:
        """
        Route message to appropriate agent.
        
        Args:
            message: User message
        
        Returns:
            Tuple of (selected_agent, confidence_score)
        """
        # Classify intent
        intent, confidence = await self._classify_intent(message)
        
        # Determine routing method based on confidence
        if confidence > self.high_confidence_threshold:
            routing_method = RoutingMethod.INTENT_CLASSIFICATION
        elif confidence > self.medium_confidence_threshold:
            routing_method = RoutingMethod.RULE_BASED
        else:
            routing_method = RoutingMethod.FALLBACK
        
        # Map intent to agent
        selected_agent = self._intent_to_agent(intent, routing_method)
        
        # Track routing metrics
        track_agent_routing(
            selected_agent=selected_agent.value,
            routing_method=routing_method.value,
            confidence_score=confidence
        )
        
        return selected_agent, confidence
    
    async def _classify_intent(self, message: str) -> Tuple[str, float]:
        """
        Classify user intent using LLM or rule-based classifier.
        
        Args:
            message: User message
        
        Returns:
            Tuple of (intent, confidence)
        """
        # Try LLM-based classification first
        try:
            result = await self.intent_classifier.classify(message)
            return result["intent"], result["confidence"]
        except Exception:
            # Fallback to rule-based
            return self._rule_based_classification(message)
    
    def _rule_based_classification(self, message: str) -> Tuple[str, float]:
        """
        Simple rule-based intent classification.
        
        Args:
            message: User message
        
        Returns:
            Tuple of (intent, confidence)
        """
        message_lower = message.lower()
        
        # Service scheduling keywords
        schedule_keywords = [
            "schedule", "appointment", "book", "reservation",
            "service appointment", "make appointment"
        ]
        if any(keyword in message_lower for keyword in schedule_keywords):
            return "schedule_service", 0.75
        
        # Technical documentation keywords
        tech_keywords = [
            "how to", "manual", "guide", "instructions",
            "documentation", "spec", "feature"
        ]
        if any(keyword in message_lower for keyword in tech_keywords):
            return "technical_question", 0.70
        
        # Troubleshooting keywords
        trouble_keywords = [
            "problem", "issue", "not working", "broken",
            "error", "fix", "repair", "diagnose"
        ]
        if any(keyword in message_lower for keyword in trouble_keywords):
            return "diagnose_problem", 0.72
        
        # Default to technical question with low confidence
        return "technical_question", 0.45
    
    def _intent_to_agent(
        self,
        intent: str,
        routing_method: RoutingMethod
    ) -> AgentType:
        """
        Map intent to agent.
        
        Args:
            intent: Classified intent
            routing_method: Method used for classification
        
        Returns:
            Agent to handle request
        """
        intent_map = {
            "technical_question": AgentType.SPECS,
            "schedule_service": AgentType.MAINTENANCE,
            "check_history": AgentType.MAINTENANCE,
            "diagnose_problem": AgentType.TROUBLESHOOT,
            "troubleshoot": AgentType.TROUBLESHOOT,
        }
        
        # Get agent from map or default to specs
        agent = intent_map.get(intent, AgentType.SPECS)
        
        # If fallback routing, always use specs as default
        if routing_method == RoutingMethod.FALLBACK:
            agent = AgentType.SPECS
        
        return agent
    
    def reroute(
        self,
        from_agent: AgentType,
        to_agent: AgentType,
        reason: RerouteReason
    ):
        """
        Track rerouting when agent realizes it's wrong.
        
        Args:
            from_agent: Original agent
            to_agent: New agent
            reason: Reason for reroute
        """
        track_agent_rerouting(
            from_agent=from_agent.value,
            to_agent=to_agent.value,
            reason=reason.value
        )
    
    async def detect_wrong_agent(
        self,
        message: str,
        current_agent: AgentType
    ) -> Optional[AgentType]:
        """
        Detect if current agent is wrong for the message.
        
        Args:
            message: User message
            current_agent: Current agent handling message
        
        Returns:
            Correct agent if mismatch detected, None otherwise
        """
        # Re-classify to see if agent is correct
        intent, confidence = await self._classify_intent(message)
        correct_agent = self._intent_to_agent(intent, RoutingMethod.INTENT_CLASSIFICATION)
        
        # If agents don't match and confidence is high enough
        if correct_agent != current_agent and confidence > 0.6:
            self.reroute(
                from_agent=current_agent,
                to_agent=correct_agent,
                reason=RerouteReason.WRONG_AGENT
            )
            return correct_agent
        
        return None


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
from orchestrator.agent_router import AgentRouter, AgentType, RerouteReason

# Initialize router
router = AgentRouter(intent_classifier)

# Route message
agent, confidence = await router.route("How to change oil?")
# Returns: (AgentType.SPECS, 0.92)
# Metrics tracked: agent_routing_total, agent_routing_confidence

# During conversation, detect if wrong agent
if await router.detect_wrong_agent(message, current_agent=AgentType.MAINTENANCE):
    correct_agent = await router.detect_wrong_agent(message, AgentType.MAINTENANCE)
    # Switch to correct agent
    # Metrics tracked: agent_rerouting_total

# Confidence levels:
# > 0.8: High confidence (intent classification)
# 0.5-0.8: Medium confidence (rule-based)
# < 0.5: Low confidence (fallback to specs)
"""
