"""Embedding service for RAG - supports OpenRouter and local models."""

from typing import List

import structlog
import httpx
from pydantic import BaseModel

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class EmbeddingResult(BaseModel):
    """Result of embedding operation."""
    
    embeddings: List[List[float]]
    model: str
    dimensions: int
    tokens_used: int = 0


class EmbeddingService:
    """Service for generating text embeddings.
    
    Supports:
    - OpenRouter API (with free models like nomic-embed)
    - OpenAI-compatible APIs
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
    ):
        self.api_key = api_key or settings.openrouter_api_key
        self.base_url = base_url or settings.openrouter_base_url
        self.model = model or settings.embedding_model
        self.dimensions = settings.embedding_dimension

    async def embed_texts(
        self,
        texts: List[str],
        batch_size: int = 100,
    ) -> EmbeddingResult:
        """Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            batch_size: Number of texts per API call
            
        Returns:
            EmbeddingResult with all embeddings
        """
        logger.info(
            "Generating embeddings",
            text_count=len(texts),
            model=self.model,
        )

        all_embeddings = []
        total_tokens = 0

        # Process in batches
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i + batch_size]
            result = await self._embed_batch(batch)
            all_embeddings.extend(result["embeddings"])
            total_tokens += result.get("tokens", 0)

        logger.info(
            "Embeddings generated",
            count=len(all_embeddings),
            dimensions=self.dimensions,
            tokens_used=total_tokens,
        )

        return EmbeddingResult(
            embeddings=all_embeddings,
            model=self.model,
            dimensions=self.dimensions,
            tokens_used=total_tokens,
        )

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding for a single query text.
        
        Args:
            text: Query text to embed
            
        Returns:
            Embedding vector
        """
        result = await self.embed_texts([text])
        return result.embeddings[0]

    async def _embed_batch(self, texts: List[str]) -> dict:
        """Call the embedding API for a batch of texts."""
        
        # Clean texts
        texts = [self._clean_text(t) for t in texts]
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "HTTP-Referer": "https://github.com/genai-auto",
                        "X-Title": "GenAI Auto RAG",
                    },
                    json={
                        "model": self.model,
                        "input": texts,
                    },
                )
                response.raise_for_status()
                data = response.json()

                # Extract embeddings from response
                embeddings = [
                    item["embedding"] 
                    for item in sorted(data["data"], key=lambda x: x["index"])
                ]
                
                tokens = data.get("usage", {}).get("total_tokens", 0)
                
                return {
                    "embeddings": embeddings,
                    "tokens": tokens,
                }

            except httpx.HTTPStatusError as e:
                logger.error(
                    "Embedding API error",
                    status_code=e.response.status_code,
                    detail=e.response.text,
                )
                raise ValueError(f"Embedding API error: {e.response.text}")

            except Exception as e:
                logger.error("Embedding generation failed", error=str(e))
                raise

    def _clean_text(self, text: str) -> str:
        """Clean text before embedding."""
        # Remove excessive whitespace
        text = " ".join(text.split())
        # Truncate if too long (most models have limits)
        max_chars = 8000  # Conservative limit
        if len(text) > max_chars:
            text = text[:max_chars]
        return text


class CachedEmbeddingService(EmbeddingService):
    """Embedding service with Redis caching."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache_prefix = "genai:embedding"

    async def embed_query(self, text: str) -> List[float]:
        """Generate embedding with caching."""
        from src.api.cache import get_redis
        import hashlib
        import json

        # Generate cache key
        text_hash = hashlib.sha256(text.encode()).hexdigest()[:16]
        cache_key = f"{self._cache_prefix}:{self.model}:{text_hash}"

        try:
            redis = await get_redis()
            cached = await redis.get(cache_key)
            
            if cached:
                logger.debug("Embedding cache hit", key=cache_key)
                return json.loads(cached)
        except Exception as e:
            logger.warning("Cache read failed", error=str(e))

        # Generate new embedding
        embedding = await super().embed_query(text)

        # Cache it
        try:
            redis = await get_redis()
            await redis.setex(
                cache_key,
                86400,  # 24 hours
                json.dumps(embedding),
            )
        except Exception as e:
            logger.warning("Cache write failed", error=str(e))

        return embedding
