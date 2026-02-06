"""
Prometheus metrics for GenAI Auto
Essential metrics: token usage, cost, latency, errors, user feedback
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from functools import wraps
import time
from typing import Callable
from fastapi import Request, Response


# ============================================================================
# ESSENTIAL METRICS
# ============================================================================

# 1. TOKEN USAGE
llm_tokens_total = Counter(
    'llm_tokens_total',
    'Total tokens used by LLM',
    ['type', 'model', 'agent']  # type: input/output
)

# 2. COST PER REQUEST
llm_cost_dollars = Counter(
    'llm_cost_dollars_total',
    'Total LLM cost in dollars',
    ['model', 'agent']
)

request_cost_histogram = Histogram(
    'request_cost_dollars',
    'Cost per request distribution',
    buckets=[0.0001, 0.001, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0]
)

# 3. RESPONSE LATENCY (P95)
request_latency_seconds = Histogram(
    'request_latency_seconds',
    'Request latency in seconds',
    ['endpoint', 'method'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

llm_latency_seconds = Histogram(
    'llm_latency_seconds',
    'LLM response time in seconds',
    ['model', 'agent'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 30.0]
)

# 4. ERROR RATE
http_errors_total = Counter(
    'http_errors_total',
    'Total HTTP errors',
    ['endpoint', 'method', 'status_code']
)

llm_errors_total = Counter(
    'llm_errors_total',
    'Total LLM errors',
    ['error_type', 'model']
)

# 5. USER FEEDBACK
user_feedback_total = Counter(
    'user_feedback_total',
    'Total user feedback',
    ['sentiment', 'message_id']  # sentiment: positive/negative
)

# ============================================================================
# ADDITIONAL USEFUL METRICS
# ============================================================================

requests_in_progress = Gauge(
    'requests_in_progress',
    'Number of requests currently being processed',
    ['endpoint']
)

chat_sessions_active = Gauge(
    'chat_sessions_active',
    'Number of active chat sessions'
)

# ============================================================================
# ADVANCED METRICS (PHASE 2)
# ============================================================================

# 6. RAG SIMILARITY SCORE
rag_similarity_score = Histogram(
    'rag_similarity_score',
    'Semantic similarity score from vector search',
    ['agent', 'document_type'],
    buckets=[0.0, 0.3, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
)

rag_documents_retrieved = Counter(
    'rag_documents_retrieved_total',
    'Total documents retrieved from vector store',
    ['agent', 'document_type']
)

rag_search_latency_ms = Histogram(
    'rag_search_latency_ms',
    'Vector search latency in milliseconds',
    ['agent'],
    buckets=[10, 25, 50, 100, 200, 500, 1000, 2000]
)

# 7. CACHE HIT RATE
cache_operations_total = Counter(
    'cache_operations_total',
    'Total cache operations',
    ['operation', 'cache_type']  # operation: hit/miss, cache_type: response/embedding
)

cache_latency_ms = Histogram(
    'cache_latency_ms',
    'Cache operation latency in milliseconds',
    ['operation', 'cache_type'],
    buckets=[1, 5, 10, 25, 50, 100, 200]
)

# 8. HANDOFF RATE
human_handoff_total = Counter(
    'human_handoff_total',
    'Total escalations to human support',
    ['reason', 'agent']  # reason: low_confidence/user_request/safety/error
)

handoff_confidence_score = Histogram(
    'handoff_confidence_score',
    'Confidence score when handoff occurred',
    buckets=[0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
)

# 9. TASK COMPLETION RATE
task_completion_total = Counter(
    'task_completion_total',
    'Total task completion tracking',
    ['status', 'agent']  # status: completed/abandoned/escalated
)

task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task completion time in seconds',
    ['agent', 'status'],
    buckets=[10, 30, 60, 120, 300, 600, 1200, 1800]  # 10s to 30min
)

# 10. AGENT ROUTING ACCURACY
agent_routing_total = Counter(
    'agent_routing_total',
    'Total agent routing decisions',
    ['selected_agent', 'routing_method']  # routing_method: intent_classification/rule_based/fallback
)

agent_routing_confidence = Histogram(
    'agent_routing_confidence',
    'Confidence score of routing decision',
    ['selected_agent'],
    buckets=[0.0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]
)

agent_rerouting_total = Counter(
    'agent_rerouting_total',
    'Total times a message was rerouted to different agent',
    ['from_agent', 'to_agent', 'reason']  # reason: wrong_agent/fallback/escalation
)


# ============================================================================
# COST CALCULATION (based on OpenRouter pricing)
# ============================================================================

# Pricing per 1M tokens (update based on actual models used)
MODEL_PRICING = {
    'meta-llama/llama-3.1-8b-instruct:free': {
        'input': 0.0,  # Free
        'output': 0.0
    },
    'google/gemma-2-9b-it:free': {
        'input': 0.0,
        'output': 0.0
    },
    'mistralai/mistral-7b-instruct:free': {
        'input': 0.0,
        'output': 0.0
    },
    # Add paid models if used
    'anthropic/claude-3-opus': {
        'input': 15.0,
        'output': 75.0
    },
    'openai/gpt-4': {
        'input': 30.0,
        'output': 60.0
    }
}


def calculate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    """
    Calculate cost in dollars for a given model and token usage.
    
    Args:
        model: Model identifier
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
    
    Returns:
        Cost in dollars
    """
    pricing = MODEL_PRICING.get(model, {'input': 0.0, 'output': 0.0})
    
    input_cost = (input_tokens / 1_000_000) * pricing['input']
    output_cost = (output_tokens / 1_000_000) * pricing['output']
    
    return input_cost + output_cost


# ============================================================================
# TRACKING HELPERS
# ============================================================================

def track_llm_call(model: str, agent: str, input_tokens: int, output_tokens: int, duration: float):
    """
    Track LLM call metrics.
    
    Args:
        model: Model identifier
        agent: Agent name (specs/maintenance/troubleshoot)
        input_tokens: Input tokens used
        output_tokens: Output tokens used
        duration: Call duration in seconds
    """
    # Token usage
    llm_tokens_total.labels(type='input', model=model, agent=agent).inc(input_tokens)
    llm_tokens_total.labels(type='output', model=model, agent=agent).inc(output_tokens)
    
    # Cost
    cost = calculate_cost(model, input_tokens, output_tokens)
    llm_cost_dollars.labels(model=model, agent=agent).inc(cost)
    request_cost_histogram.observe(cost)
    
    # Latency
    llm_latency_seconds.labels(model=model, agent=agent).observe(duration)


def track_user_feedback(message_id: str, sentiment: str):
    """
    Track user feedback (thumbs up/down).
    
    Args:
        message_id: ID of the message being rated
        sentiment: 'positive' or 'negative'
    """
    user_feedback_total.labels(sentiment=sentiment, message_id=message_id).inc()


def track_llm_error(error_type: str, model: str):
    """
    Track LLM errors.
    
    Args:
        error_type: Type of error (timeout, rate_limit, api_error, etc.)
        model: Model identifier
    """
    llm_errors_total.labels(error_type=error_type, model=model).inc()


# ============================================================================
# ADVANCED TRACKING HELPERS (PHASE 2)
# ============================================================================

def track_rag_retrieval(
    agent: str,
    document_type: str,
    similarity_scores: list[float],
    search_latency_ms: float
):
    """
    Track RAG retrieval metrics.
    
    Args:
        agent: Agent name (specs/maintenance/troubleshoot)
        document_type: Type of documents retrieved (manual/spec/faq/etc)
        similarity_scores: List of similarity scores for retrieved docs
        search_latency_ms: Vector search latency in milliseconds
    
    Example:
        track_rag_retrieval(
            agent="specs",
            document_type="manual",
            similarity_scores=[0.89, 0.85, 0.82, 0.78, 0.75],
            search_latency_ms=45.2
        )
    """
    # Track each similarity score
    for score in similarity_scores:
        rag_similarity_score.labels(
            agent=agent,
            document_type=document_type
        ).observe(score)
    
    # Count retrieved documents
    rag_documents_retrieved.labels(
        agent=agent,
        document_type=document_type
    ).inc(len(similarity_scores))
    
    # Track search latency
    rag_search_latency_ms.labels(agent=agent).observe(search_latency_ms)


def track_cache_operation(
    operation: str,
    cache_type: str,
    latency_ms: float
):
    """
    Track cache operations (hit/miss).
    
    Args:
        operation: 'hit' or 'miss'
        cache_type: 'response' or 'embedding'
        latency_ms: Operation latency in milliseconds
    
    Example:
        # Cache hit
        track_cache_operation(
            operation="hit",
            cache_type="embedding",
            latency_ms=2.5
        )
        
        # Cache miss
        track_cache_operation(
            operation="miss",
            cache_type="response",
            latency_ms=150.0
        )
    """
    cache_operations_total.labels(
        operation=operation,
        cache_type=cache_type
    ).inc()
    
    cache_latency_ms.labels(
        operation=operation,
        cache_type=cache_type
    ).observe(latency_ms)


def track_human_handoff(
    reason: str,
    agent: str,
    confidence_score: float | None = None
):
    """
    Track escalation to human support.
    
    Args:
        reason: Reason for handoff (low_confidence/user_request/safety/error)
        agent: Agent that triggered handoff
        confidence_score: Confidence score when handoff occurred (0-1)
    
    Example:
        track_human_handoff(
            reason="low_confidence",
            agent="specs",
            confidence_score=0.45
        )
    """
    human_handoff_total.labels(
        reason=reason,
        agent=agent
    ).inc()
    
    if confidence_score is not None:
        handoff_confidence_score.observe(confidence_score)


def track_task_completion(
    status: str,
    agent: str,
    duration_seconds: float
):
    """
    Track task completion.
    
    Args:
        status: Task status (completed/abandoned/escalated)
        agent: Agent that handled the task
        duration_seconds: How long the task took
    
    Example:
        track_task_completion(
            status="completed",
            agent="maintenance",
            duration_seconds=125.5
        )
    """
    task_completion_total.labels(
        status=status,
        agent=agent
    ).inc()
    
    task_duration_seconds.labels(
        agent=agent,
        status=status
    ).observe(duration_seconds)


def track_agent_routing(
    selected_agent: str,
    routing_method: str,
    confidence_score: float
):
    """
    Track agent routing decisions.
    
    Args:
        selected_agent: Agent selected (specs/maintenance/troubleshoot)
        routing_method: How agent was selected (intent_classification/rule_based/fallback)
        confidence_score: Confidence in routing decision (0-1)
    
    Example:
        track_agent_routing(
            selected_agent="specs",
            routing_method="intent_classification",
            confidence_score=0.92
        )
    """
    agent_routing_total.labels(
        selected_agent=selected_agent,
        routing_method=routing_method
    ).inc()
    
    agent_routing_confidence.labels(
        selected_agent=selected_agent
    ).observe(confidence_score)


def track_agent_rerouting(
    from_agent: str,
    to_agent: str,
    reason: str
):
    """
    Track when a message is rerouted to a different agent.
    
    Args:
        from_agent: Original agent
        to_agent: New agent
        reason: Why rerouting occurred (wrong_agent/fallback/escalation)
    
    Example:
        track_agent_rerouting(
            from_agent="maintenance",
            to_agent="specs",
            reason="wrong_agent"
        )
    """
    agent_rerouting_total.labels(
        from_agent=from_agent,
        to_agent=to_agent,
        reason=reason
    ).inc()


# ============================================================================
# FASTAPI MIDDLEWARE
# ============================================================================

async def metrics_middleware(request: Request, call_next: Callable):
    """
    Middleware to track request metrics automatically.
    """
    endpoint = request.url.path
    method = request.method
    
    # Track in-progress requests
    requests_in_progress.labels(endpoint=endpoint).inc()
    
    # Track latency
    start_time = time.time()
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        # Record latency
        request_latency_seconds.labels(endpoint=endpoint, method=method).observe(duration)
        
        # Track errors
        if response.status_code >= 400:
            http_errors_total.labels(
                endpoint=endpoint,
                method=method,
                status_code=response.status_code
            ).inc()
        
        return response
    
    except Exception as e:
        duration = time.time() - start_time
        request_latency_seconds.labels(endpoint=endpoint, method=method).observe(duration)
        
        # Track 500 errors
        http_errors_total.labels(
            endpoint=endpoint,
            method=method,
            status_code=500
        ).inc()
        
        raise
    
    finally:
        requests_in_progress.labels(endpoint=endpoint).dec()


# ============================================================================
# METRICS ENDPOINT
# ============================================================================

def get_metrics() -> Response:
    """
    Generate Prometheus metrics for scraping.
    
    Returns:
        Response with Prometheus metrics
    """
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )


# ============================================================================
# DECORATOR FOR EASY TRACKING
# ============================================================================

def track_endpoint_metrics(endpoint_name: str):
    """
    Decorator to automatically track endpoint metrics.
    
    Usage:
        @track_endpoint_metrics('chat')
        async def chat_endpoint():
            ...
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            requests_in_progress.labels(endpoint=endpoint_name).inc()
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                request_latency_seconds.labels(
                    endpoint=endpoint_name,
                    method='POST'
                ).observe(duration)
                return result
            
            finally:
                requests_in_progress.labels(endpoint=endpoint_name).dec()
        
        return wrapper
    return decorator
