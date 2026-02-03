"""Application configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://genai:genai_secret@localhost:5432/genai_auto"

    # LLM Provider (OpenRouter)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "meta-llama/llama-3.1-8b-instruct:free"  # Free model
    
    # Embeddings (using free local model or OpenRouter)
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"  # Free on OpenRouter
    embedding_dimension: int = 768  # Nomic embed dimension

    # LangChain Observability
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""

    # Application
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # JWT Authentication (built-in, lightweight)
    jwt_secret_key: str = "change-me-in-production-use-openssl-rand-hex-32"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # Redis Cache (Performance)
    redis_url: str = "redis://localhost:6379"
    cache_ttl: int = 3600  # 1 hour default
    cache_enabled: bool = True

    # Human Handoff
    confidence_threshold: float = 0.7  # Below this, escalate to human
    human_support_webhook: str = ""  # Webhook to notify human support

    # Scheduler API
    scheduler_api_url: str = "http://localhost:9000"
    scheduler_api_key: str = ""

    # Vector search
    similarity_top_k: int = 5

    # PII Protection
    mask_pii: bool = True  # Mask sensitive data in logs

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
