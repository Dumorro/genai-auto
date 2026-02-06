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
