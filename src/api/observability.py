"""Observability module for request tracing and monitoring."""

import time
import uuid
from typing import Optional, Callable
from contextvars import ContextVar
from functools import wraps

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Context variable for request tracing
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
session_id_ctx: ContextVar[Optional[str]] = ContextVar("session_id", default=None)


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for end-to-end request tracing."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Generate or extract request ID
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request_id_ctx.set(request_id)

        # Extract session ID if present
        session_id = request.headers.get("X-Session-ID")
        if session_id:
            session_id_ctx.set(session_id)

        # Start timing
        start_time = time.perf_counter()

        # Log request
        logger.info(
            "Request started",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else None,
        )

        try:
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000

            # Add tracing headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Response-Time"] = f"{duration_ms:.2f}ms"

            # Log response
            logger.info(
                "Request completed",
                request_id=request_id,
                status_code=response.status_code,
                duration_ms=round(duration_ms, 2),
            )

            return response

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "Request failed",
                request_id=request_id,
                error=str(e),
                duration_ms=round(duration_ms, 2),
            )
            raise


class MetricsCollector:
    """Collect and expose metrics for monitoring."""

    def __init__(self):
        self.request_count = 0
        self.error_count = 0
        self.total_latency_ms = 0
        self.agent_usage = {
            "specs": 0,
            "maintenance": 0,
            "troubleshoot": 0,
        }
        self.escalation_count = 0
        self.cache_hits = 0
        self.cache_misses = 0

    def record_request(self, latency_ms: float, success: bool = True):
        """Record a request."""
        self.request_count += 1
        self.total_latency_ms += latency_ms
        if not success:
            self.error_count += 1

    def record_agent_usage(self, agent: str):
        """Record which agent was used."""
        if agent in self.agent_usage:
            self.agent_usage[agent] += 1

    def record_escalation(self):
        """Record an escalation to human support."""
        self.escalation_count += 1

    def record_cache_hit(self):
        """Record a cache hit."""
        self.cache_hits += 1

    def record_cache_miss(self):
        """Record a cache miss."""
        self.cache_misses += 1

    def get_metrics(self) -> dict:
        """Get current metrics."""
        avg_latency = (
            self.total_latency_ms / self.request_count
            if self.request_count > 0
            else 0
        )
        cache_hit_rate = (
            self.cache_hits / (self.cache_hits + self.cache_misses)
            if (self.cache_hits + self.cache_misses) > 0
            else 0
        )

        return {
            "requests": {
                "total": self.request_count,
                "errors": self.error_count,
                "error_rate": self.error_count / self.request_count if self.request_count > 0 else 0,
            },
            "latency": {
                "average_ms": round(avg_latency, 2),
                "total_ms": round(self.total_latency_ms, 2),
            },
            "agents": self.agent_usage,
            "escalations": self.escalation_count,
            "cache": {
                "hits": self.cache_hits,
                "misses": self.cache_misses,
                "hit_rate": round(cache_hit_rate, 3),
            },
        }


def trace_operation(operation_name: str):
    """Decorator for tracing individual operations."""

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            request_id = request_id_ctx.get()
            start_time = time.perf_counter()

            logger.debug(
                f"Operation started: {operation_name}",
                request_id=request_id,
                operation=operation_name,
            )

            try:
                result = await func(*args, **kwargs)

                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.debug(
                    f"Operation completed: {operation_name}",
                    request_id=request_id,
                    operation=operation_name,
                    duration_ms=round(duration_ms, 2),
                )

                return result

            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                logger.error(
                    f"Operation failed: {operation_name}",
                    request_id=request_id,
                    operation=operation_name,
                    error=str(e),
                    duration_ms=round(duration_ms, 2),
                )
                raise

        return wrapper
    return decorator


# Global metrics collector
metrics = MetricsCollector()
