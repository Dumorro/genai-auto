"""Application configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Database
    database_url: str = "postgresql://genai:genai_secret@localhost:5432/genai_auto"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4-turbo-preview"
    openai_embedding_model: str = "text-embedding-3-small"

    # LangChain
    langchain_tracing_v2: bool = False
    langchain_api_key: str = ""

    # Application
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    debug: bool = False

    # Scheduler API
    scheduler_api_url: str = "http://localhost:9000"
    scheduler_api_key: str = ""

    # Vector search
    vector_dimension: int = 1536
    similarity_top_k: int = 5

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
