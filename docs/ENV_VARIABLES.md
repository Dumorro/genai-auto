# Environment Variables

Complete reference for all configuration variables used by GenAI Auto.

---

## Quick Setup

Copy the example file and edit:

```bash
cp .env.example .env
```

The application loads variables from `.env` automatically via Pydantic `BaseSettings`.

---

## Variable Reference

### Database

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `DATABASE_URL` | Yes | `postgresql://genai:genai_secret@localhost:5432/genai_auto` | PostgreSQL connection string |
| `POSTGRES_USER` | Yes | `genai` | PostgreSQL username (Docker) |
| `POSTGRES_PASSWORD` | Yes | `genai_secret` | PostgreSQL password (Docker) |
| `POSTGRES_DB` | Yes | `genai_auto` | PostgreSQL database name (Docker) |

**Notes**:
- `POSTGRES_*` variables are used by the Docker PostgreSQL container
- `DATABASE_URL` is used by the application (SQLAlchemy)
- For Docker: use `postgres` as hostname (service name)
- For local: use `localhost`

### LLM Provider (OpenRouter)

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `OPENROUTER_API_KEY` | Yes | `""` (empty) | API key from [openrouter.ai](https://openrouter.ai) |
| `OPENROUTER_BASE_URL` | No | `https://openrouter.ai/api/v1` | OpenRouter API base URL |
| `LLM_MODEL` | No | `meta-llama/llama-3.1-8b-instruct:free` | LLM model identifier |

**Free Model Options**:

| Model | ID | Best For |
|-------|----|----------|
| Llama 3.1 8B | `meta-llama/llama-3.1-8b-instruct:free` | General chat (default) |
| DeepSeek R1 Chimera | `tngtech/deepseek-r1t2-chimera:free` | Reasoning tasks |
| Gemma 2 9B | `google/gemma-2-9b-it:free` | General purpose |
| Mistral 7B | `mistralai/mistral-7b-instruct:free` | Fast responses |
| Qwen 2 7B | `qwen/qwen-2-7b-instruct:free` | Multilingual |

**Important**: The Maintenance Agent requires a model with **function calling** support. Free models may not support this. For full functionality, use `openai/gpt-4o-mini` or `anthropic/claude-3.5-sonnet`.

### Embeddings

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `EMBEDDING_MODEL` | No | `nomic-ai/nomic-embed-text-v1.5` | Embedding model for RAG |
| `EMBEDDING_DIMENSION` | No | `768` | Vector dimension (must match model output) |

**Note**: If you change the embedding model, ensure `EMBEDDING_DIMENSION` matches the model's output dimension. Mismatched dimensions will cause vector store errors.

### Authentication (JWT)

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `JWT_SECRET_KEY` | Yes | `change-me-in-production-use-openssl-rand-hex-32` | JWT signing secret |
| `JWT_ALGORITHM` | No | `HS256` | JWT algorithm |
| `JWT_ACCESS_EXPIRE_MINUTES` | No | `30` | Access token TTL (minutes) |
| `JWT_REFRESH_EXPIRE_DAYS` | No | `7` | Refresh token TTL (days) |

**Production**: Generate a strong secret with:
```bash
openssl rand -hex 32
```

### Redis Cache

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379` | Redis connection URL |
| `CACHE_TTL` | No | `3600` | Default cache TTL in seconds (1 hour) |
| `CACHE_ENABLED` | No | `true` | Enable/disable caching |

**Note**: Embedding cache uses a separate 24-hour TTL regardless of `CACHE_TTL`.

### Human Handoff

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `CONFIDENCE_THRESHOLD` | No | `0.7` | Score below this triggers escalation |
| `HUMAN_SUPPORT_WEBHOOK` | No | `""` (empty) | Webhook URL for escalation notifications |

### Privacy & Security

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `MASK_PII` | No | `true` | Mask PII (SSN, email, phone, etc.) in logs |

### Application

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `API_HOST` | No | `0.0.0.0` | API server bind address |
| `API_PORT` | No | `8000` | API server port |
| `LOG_LEVEL` | No | `INFO` | Log level: DEBUG, INFO, WARNING, ERROR |
| `DEBUG` | No | `false` | Enable debug mode |

### Observability

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `LANGCHAIN_TRACING_V2` | No | `false` | Enable LangSmith tracing |
| `LANGCHAIN_API_KEY` | No | `""` (empty) | LangSmith API key |

### External Integrations

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `SCHEDULER_API_URL` | No | `http://localhost:9000` | External scheduler API URL |
| `SCHEDULER_API_KEY` | No | `""` (empty) | Scheduler API key |

### Optional Tools (Docker)

| Variable | Required | Default | Description |
|----------|:--------:|---------|-------------|
| `PGADMIN_EMAIL` | No | `admin@genai.local` | PGAdmin login email |
| `PGADMIN_PASSWORD` | No | `admin` | PGAdmin login password |

Start PGAdmin with:
```bash
docker-compose --profile tools up pgadmin
```

---

## Environment Profiles

### Development (Local)

```bash
DATABASE_URL=postgresql://genai:genai_secret@localhost:5432/genai_auto
REDIS_URL=redis://localhost:6379
LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
LOG_LEVEL=DEBUG
DEBUG=true
CACHE_ENABLED=false
```

### Development (Docker)

```bash
DATABASE_URL=postgresql://genai:genai_secret@postgres:5432/genai_auto
REDIS_URL=redis://redis:6379
LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
LOG_LEVEL=INFO
```

### Production

```bash
DATABASE_URL=postgresql://genai:<strong-password>@postgres:5432/genai_auto
POSTGRES_PASSWORD=<strong-password>
JWT_SECRET_KEY=<openssl rand -hex 32>
LLM_MODEL=openai/gpt-4o-mini  # Or other function-calling model
LOG_LEVEL=WARNING
DEBUG=false
MASK_PII=true
CACHE_ENABLED=true
```

---

## Source Files

- Settings class: `src/api/config.py`
- Example file: `.env.example`
