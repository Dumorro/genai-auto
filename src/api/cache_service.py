"""
Cache service with integrated metrics tracking.
"""

import time
import json
import hashlib
from typing import Any, Optional
from redis import asyncio as aioredis
from .metrics import track_cache_operation


class CacheService:
    """
    Redis cache with automatic metrics tracking.
    """
    
    def __init__(self, redis_client: aioredis.Redis):
        self.redis = redis_client
    
    async def get(
        self,
        key: str,
        cache_type: str = "response"
    ) -> Optional[Any]:
        """
        Get value from cache with metrics tracking.
        
        Args:
            key: Cache key
            cache_type: Type of cached data (response/embedding)
        
        Returns:
            Cached value or None if miss
        """
        start_time = time.time()
        
        try:
            value = await self.redis.get(key)
            latency_ms = (time.time() - start_time) * 1000
            
            if value is not None:
                # Cache hit
                track_cache_operation(
                    operation="hit",
                    cache_type=cache_type,
                    latency_ms=latency_ms
                )
                return json.loads(value)
            else:
                # Cache miss
                track_cache_operation(
                    operation="miss",
                    cache_type=cache_type,
                    latency_ms=latency_ms
                )
                return None
        
        except Exception:
            latency_ms = (time.time() - start_time) * 1000
            track_cache_operation(
                operation="miss",
                cache_type=cache_type,
                latency_ms=latency_ms
            )
            return None
    
    async def set(
        self,
        key: str,
        value: Any,
        ttl: int = 3600,
        cache_type: str = "response"
    ):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            cache_type: Type of cached data
        """
        try:
            await self.redis.setex(
                key,
                ttl,
                json.dumps(value)
            )
        except Exception:
            pass  # Silent fail for cache writes
    
    async def delete(self, key: str):
        """Delete key from cache."""
        try:
            await self.redis.delete(key)
        except Exception:
            pass
    
    async def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern."""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
        except Exception:
            pass


class EmbeddingCache:
    """
    Specialized cache for embeddings with metrics.
    """
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
    
    def _make_key(self, text: str) -> str:
        """Generate cache key from text."""
        text_hash = hashlib.md5(text.encode()).hexdigest()
        return f"embedding:{text_hash}"
    
    async def get_embedding(self, text: str) -> Optional[list]:
        """
        Get cached embedding for text.
        
        Args:
            text: Text to get embedding for
        
        Returns:
            Embedding vector or None if miss
        """
        key = self._make_key(text)
        return await self.cache.get(key, cache_type="embedding")
    
    async def cache_embedding(
        self,
        text: str,
        embedding: list,
        ttl: int = 86400  # 24 hours
    ):
        """
        Cache embedding for text.
        
        Args:
            text: Text that was embedded
            embedding: Embedding vector
            ttl: Cache TTL in seconds
        """
        key = self._make_key(text)
        await self.cache.set(key, embedding, ttl=ttl, cache_type="embedding")


class ResponseCache:
    """
    Specialized cache for LLM responses with metrics.
    """
    
    def __init__(self, cache_service: CacheService):
        self.cache = cache_service
    
    def _make_key(self, message: str, context: str = "") -> str:
        """Generate cache key from message + context."""
        combined = f"{message}:{context}"
        key_hash = hashlib.md5(combined.encode()).hexdigest()
        return f"response:{key_hash}"
    
    async def get_response(
        self,
        message: str,
        context: str = ""
    ) -> Optional[dict]:
        """
        Get cached response for message.
        
        Args:
            message: User message
            context: Optional context string
        
        Returns:
            Cached response or None
        """
        key = self._make_key(message, context)
        return await self.cache.get(key, cache_type="response")
    
    async def cache_response(
        self,
        message: str,
        response: dict,
        context: str = "",
        ttl: int = 3600  # 1 hour
    ):
        """
        Cache LLM response.
        
        Args:
            message: User message
            response: LLM response dict
            context: Optional context
            ttl: Cache TTL
        """
        key = self._make_key(message, context)
        await self.cache.set(key, response, ttl=ttl, cache_type="response")


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
from api.cache_service import CacheService, EmbeddingCache, ResponseCache
from redis import asyncio as aioredis

# Initialize
redis = aioredis.from_url("redis://localhost:6379")
cache_service = CacheService(redis)
embedding_cache = EmbeddingCache(cache_service)
response_cache = ResponseCache(cache_service)

# Embedding cache
cached_emb = await embedding_cache.get_embedding("some text")
if not cached_emb:
    # Cache miss - generate embedding
    embedding = await generate_embedding("some text")
    await embedding_cache.cache_embedding("some text", embedding)
    # Metrics tracked automatically: cache_operations_total{operation="miss"}
else:
    # Cache hit
    embedding = cached_emb
    # Metrics tracked: cache_operations_total{operation="hit"}

# Response cache
cached_resp = await response_cache.get_response("Hello", _context ="session_123")
if not cached_resp:
    # Generate response
    response = await llm.generate("Hello")
    await response_cache.cache_response("Hello", response, _context ="session_123")
"""
