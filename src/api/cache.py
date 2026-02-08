"""Redis caching for performance optimization."""

import json
import hashlib
from typing import Optional

import structlog
import redis.asyncio as redis

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Global Redis connection pool
_redis_pool: Optional[redis.Redis] = None


async def get_redis() -> redis.Redis:
    """Get Redis connection."""
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = redis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    
    return _redis_pool


async def close_redis():
    """Close Redis connection."""
    global _redis_pool
    
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


class ResponseCache:
    """Cache for AI responses to reduce latency and costs."""

    def __init__(self, prefix: str = "genai:response"):
        self.prefix = prefix
        self.ttl = settings.cache_ttl
        self.enabled = settings.cache_enabled

    def _generate_key(self, query: str, context: dict = None) -> str:
        """Generate cache key from query and context."""
        key_data = {"query": query.lower().strip()}
        if context:
            key_data["context"] = sorted(context.items())
        
        key_hash = hashlib.sha256(
            json.dumps(key_data, sort_keys=True).encode()
        ).hexdigest()[:16]
        
        return f"{self.prefix}:{key_hash}"

    async def get(self, query: str, context: dict = None) -> Optional[str]:
        """Get cached response."""
        if not self.enabled:
            return None

        try:
            r = await get_redis()
            key = self._generate_key(query, context)
            cached = await r.get(key)
            
            if cached:
                logger.info("Cache hit", key=key)
                return cached
            
            logger.debug("Cache miss", key=key)
            return None

        except Exception as e:
            logger.warning("Cache get failed", error=str(e))
            return None

    async def set(self, query: str, response: str, context: dict = None, ttl: int = None):
        """Cache a response."""
        if not self.enabled:
            return

        try:
            r = await get_redis()
            key = self._generate_key(query, context)
            await r.setex(key, ttl or self.ttl, response)
            logger.debug("Response cached", key=key, ttl=ttl or self.ttl)

        except Exception as e:
            logger.warning("Cache set failed", error=str(e))

    async def invalidate(self, pattern: str = None):
        """Invalidate cached responses."""
        try:
            r = await get_redis()
            if pattern:
                keys = await r.keys(f"{self.prefix}:{pattern}*")
            else:
                keys = await r.keys(f"{self.prefix}:*")
            
            if keys:
                await r.delete(*keys)
                logger.info("Cache invalidated", count=len(keys))

        except Exception as e:
            logger.warning("Cache invalidation failed", error=str(e))


class TokenUsageTracker:
    """Track token usage for cost monitoring."""

    def __init__(self, prefix: str = "genai:tokens"):
        self.prefix = prefix

    async def record_usage(
        self,
        session_id: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ):
        """Record token usage."""
        try:
            r = await get_redis()
            
            # Daily key for aggregation
            from datetime import datetime
            date_key = datetime.utcnow().strftime("%Y-%m-%d")
            
            # Increment counters
            pipe = r.pipeline()
            pipe.hincrby(f"{self.prefix}:daily:{date_key}", f"{model}:input", input_tokens)
            pipe.hincrby(f"{self.prefix}:daily:{date_key}", f"{model}:output", output_tokens)
            pipe.hincrby(f"{self.prefix}:session:{session_id}", "input", input_tokens)
            pipe.hincrby(f"{self.prefix}:session:{session_id}", "output", output_tokens)
            await pipe.execute()

            logger.debug(
                "Token usage recorded",
                session_id=session_id,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
            )

        except Exception as e:
            logger.warning("Failed to record token usage", error=str(e))

    async def get_daily_usage(self, date: str = None) -> dict:
        """Get daily token usage statistics."""
        try:
            r = await get_redis()
            
            if not date:
                from datetime import datetime
                date = datetime.utcnow().strftime("%Y-%m-%d")
            
            usage = await r.hgetall(f"{self.prefix}:daily:{date}")
            return {k: int(v) for k, v in usage.items()}

        except Exception as e:
            logger.warning("Failed to get daily usage", error=str(e))
            return {}

    async def get_session_usage(self, session_id: str) -> dict:
        """Get session token usage."""
        try:
            r = await get_redis()
            usage = await r.hgetall(f"{self.prefix}:session:{session_id}")
            return {k: int(v) for k, v in usage.items()}

        except Exception as e:
            logger.warning("Failed to get session usage", error=str(e))
            return {}


# Global instances
response_cache = ResponseCache()
token_tracker = TokenUsageTracker()
