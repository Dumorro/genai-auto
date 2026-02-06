"""
Advanced Metrics Integration Examples (Phase 2)

This file demonstrates how to integrate the 5 advanced metrics:
6. RAG similarity score
7. Cache hit rate
8. Handoff rate
9. Task completion rate
10. Agent routing accuracy
"""

from fastapi import APIRouter
from pydantic import BaseModel
import time
from ..metrics import (
    track_rag_retrieval,
    track_cache_operation,
    track_human_handoff,
    track_task_completion,
    track_agent_routing,
    track_agent_rerouting
)


router = APIRouter(prefix="/api/v1", tags=["examples"])


# ============================================================================
# EXAMPLE 1: RAG RETRIEVAL WITH METRICS
# ============================================================================

class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 5


async def search_documents_with_metrics(query: str, top_k: int = 5):
    """
    Example: RAG search with similarity score tracking.
    
    Replace this with your actual RAG pipeline.
    """
    # Simulate vector search
    start_time = time.time()
    
    # TODO: Replace with actual vector search
    # results = await vector_store.similarity_search(query, k=top_k)
    
    # Simulated results
    results = [
        {"content": "doc 1", "similarity": 0.89, "type": "manual"},
        {"content": "doc 2", "similarity": 0.85, "type": "manual"},
        {"content": "doc 3", "similarity": 0.82, "type": "manual"},
        {"content": "doc 4", "similarity": 0.78, "type": "spec"},
        {"content": "doc 5", "similarity": 0.75, "type": "spec"},
    ]
    
    search_latency_ms = (time.time() - start_time) * 1000
    
    # ====================================================================
    # TRACK RAG METRICS
    # ====================================================================
    similarity_scores = [r["similarity"] for r in results]
    document_type = "manual"  # Or determine dominant type
    
    track_rag_retrieval(
        agent="specs",
        document_type=document_type,
        similarity_scores=similarity_scores,
        search_latency_ms=search_latency_ms
    )
    
    return results


# ============================================================================
# EXAMPLE 2: CACHE WITH METRICS
# ============================================================================

async def get_embedding_with_cache(text: str):
    """
    Example: Get embedding with cache hit/miss tracking.
    """
    start_time = time.time()
    
    # Try cache first
    # cached = await cache.get(f"embedding:{hash(text)}")
    cached = None  # Simulate
    
    if cached:
        latency_ms = (time.time() - start_time) * 1000
        track_cache_operation(
            operation="hit",
            cache_type="embedding",
            latency_ms=latency_ms
        )
        return cached
    
    # Cache miss - generate embedding
    # embedding = await embedding_model.embed(text)
    embedding = [0.1] * 1536  # Simulate
    
    latency_ms = (time.time() - start_time) * 1000
    track_cache_operation(
        operation="miss",
        cache_type="embedding",
        latency_ms=latency_ms
    )
    
    # Store in cache
    # await cache.set(f"embedding:{hash(text)}", embedding, ttl=3600)
    
    return embedding


# ============================================================================
# EXAMPLE 3: HUMAN HANDOFF WITH METRICS
# ============================================================================

async def check_confidence_and_handoff(response: dict, agent: str):
    """
    Example: Check confidence and trigger handoff if needed.
    """
    confidence = response.get("confidence", 1.0)
    threshold = 0.7
    
    if confidence < threshold:
        # Trigger handoff
        track_human_handoff(
            reason="low_confidence",
            agent=agent,
            confidence_score=confidence
        )
        
        return {
            "handoff": True,
            "reason": "Low confidence - escalating to human support",
            "confidence": confidence
        }
    
    return {"handoff": False}


async def handle_explicit_handoff_request(message: str, agent: str):
    """
    Example: User explicitly asks for human help.
    """
    # Check if user wants human help
    handoff_keywords = ["talk to human", "speak to agent", "human support"]
    if any(keyword in message.lower() for keyword in handoff_keywords):
        track_human_handoff(
            reason="user_request",
            agent=agent,
            confidence_score=None  # User requested, not confidence-based
        )
        return True
    
    return False


# ============================================================================
# EXAMPLE 4: TASK COMPLETION WITH METRICS
# ============================================================================

class ChatSession:
    """Simplified session tracking for example."""
    def __init__(self, session_id: str, agent: str):
        self.session_id = session_id
        self.agent = agent
        self.start_time = time.time()
        self.status = "active"
    
    def complete(self, status: str):
        """Mark session as complete and track metrics."""
        duration = time.time() - self.start_time
        
        track_task_completion(
            status=status,
            agent=self.agent,
            duration_seconds=duration
        )
        
        self.status = status


# Usage:
# session = ChatSession("sess_123", "maintenance")
# ... chat interaction ...
# session.complete("completed")  # or "abandoned" or "escalated"


# ============================================================================
# EXAMPLE 5: AGENT ROUTING WITH METRICS
# ============================================================================

async def route_message_to_agent(message: str):
    """
    Example: Route message to appropriate agent with metrics.
    """
    # Classify intent (replace with actual classifier)
    intent, confidence = await classify_intent(message)
    
    # Determine routing method
    if confidence > 0.8:
        routing_method = "intent_classification"
    elif confidence > 0.5:
        routing_method = "rule_based"
    else:
        routing_method = "fallback"
    
    # Select agent based on intent
    agent_map = {
        "technical_question": "specs",
        "schedule_service": "maintenance",
        "diagnose_problem": "troubleshoot"
    }
    selected_agent = agent_map.get(intent, "specs")  # Default to specs
    
    # Track routing decision
    track_agent_routing(
        selected_agent=selected_agent,
        routing_method=routing_method,
        confidence_score=confidence
    )
    
    return selected_agent, confidence


async def classify_intent(message: str):
    """
    Simulate intent classification.
    Replace with actual LLM-based classifier.
    """
    # Simplified rules
    if "schedule" in message.lower() or "appointment" in message.lower():
        return "schedule_service", 0.92
    elif "how to" in message.lower() or "manual" in message.lower():
        return "technical_question", 0.88
    elif "problem" in message.lower() or "not working" in message.lower():
        return "diagnose_problem", 0.85
    else:
        return "technical_question", 0.55  # Low confidence


async def handle_wrong_agent_reroute(
    message: str,
    current_agent: str,
    actual_intent: str
):
    """
    Example: Reroute when agent realizes it's the wrong one.
    """
    agent_map = {
        "technical_question": "specs",
        "schedule_service": "maintenance",
        "diagnose_problem": "troubleshoot"
    }
    correct_agent = agent_map.get(actual_intent, "specs")
    
    if correct_agent != current_agent:
        track_agent_rerouting(
            from_agent=current_agent,
            to_agent=correct_agent,
            reason="wrong_agent"
        )
        return correct_agent
    
    return current_agent


# ============================================================================
# INTEGRATION SUMMARY
# ============================================================================

"""
INTEGRATION CHECKLIST:

1. RAG Similarity Score:
   ✓ Track after every vector search
   ✓ Include all retrieved document scores
   ✓ Measure search latency
   
2. Cache Hit Rate:
   ✓ Track on every cache get operation
   ✓ Measure cache operation latency
   ✓ Track both hits and misses
   
3. Handoff Rate:
   ✓ Track when confidence < threshold
   ✓ Track user-requested handoffs
   ✓ Track safety-triggered handoffs
   ✓ Record confidence at handoff time
   
4. Task Completion Rate:
   ✓ Track at session/conversation end
   ✓ Record completion status (completed/abandoned/escalated)
   ✓ Measure task duration
   
5. Agent Routing Accuracy:
   ✓ Track every routing decision
   ✓ Record routing method (intent/rules/fallback)
   ✓ Track confidence score
   ✓ Track rerouting events

PROMETHEUS QUERIES:

# RAG quality (average similarity)
avg(rag_similarity_score)

# Cache hit rate
rate(cache_operations_total{operation="hit"}[5m]) / rate(cache_operations_total[5m])

# Handoff rate (per hour)
rate(human_handoff_total[1h]) * 3600

# Task completion rate
rate(task_completion_total{status="completed"}[1h]) / rate(task_completion_total[1h])

# Agent routing accuracy (high confidence %)
rate(agent_routing_confidence_bucket{le="0.8"}[5m]) / rate(agent_routing_confidence_count[5m])

# Rerouting rate (indication of routing errors)
rate(agent_rerouting_total[5m])
"""
