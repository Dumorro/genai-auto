# Development Guide

## Prerequisites

- Python 3.10+
- Docker & Docker Compose
- Git
- OpenRouter API key ([openrouter.ai](https://openrouter.ai))

---

## Local Setup

### With Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/Dumorro/genai-auto.git
cd genai-auto

# Copy environment file
cp .env.example .env
# Edit .env with your OPENROUTER_API_KEY

# Start all services
docker-compose up -d

# Verify services
curl http://localhost:8000/health
```

### Without Docker

```bash
# Clone and setup
git clone https://github.com/Dumorro/genai-auto.git
cd genai-auto

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/macOS
# venv\Scripts\activate   # Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env:
#   DATABASE_URL=postgresql://genai:genai_secret@localhost:5432/genai_auto
#   REDIS_URL=redis://localhost:6379

# Start external services (PostgreSQL + Redis required)
docker-compose up -d postgres redis

# Run database migrations
alembic upgrade head

# Start the API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Project Structure

```
genai-auto/
├── src/
│   ├── api/                        # FastAPI application
│   │   ├── main.py                 # App entry point, middleware, routers
│   │   ├── config.py               # Pydantic settings (env vars)
│   │   ├── cache.py                # Redis cache client
│   │   ├── pii.py                  # PII masking utilities
│   │   ├── handoff.py              # Human handoff manager
│   │   ├── observability.py        # Request tracing middleware
│   │   ├── auth/
│   │   │   └── jwt_auth.py         # JWT authentication (Argon2)
│   │   └── routes/
│   │       ├── auth.py             # Auth endpoints (register, login, refresh)
│   │       ├── chat.py             # Chat endpoint (POST /api/v1/chat)
│   │       ├── documents.py        # Document management (upload, search)
│   │       ├── health.py           # Health check endpoints
│   │       ├── metrics_routes.py   # Prometheus metrics + feedback
│   │       ├── evaluation.py       # RAG evaluation endpoints
│   │       └── websocket.py        # WebSocket chat endpoint
│   ├── agents/                     # Specialized AI agents
│   │   ├── specs/
│   │   │   └── agent.py            # Specs Agent (RAG-powered)
│   │   ├── maintenance/
│   │   │   └── agent.py            # Maintenance Agent (tool-calling)
│   │   └── troubleshoot/
│   │       └── agent.py            # Troubleshoot Agent (diagnostics)
│   ├── orchestrator/               # LangGraph orchestration
│   │   ├── graph.py                # StateGraph workflow definition
│   │   ├── agent_router.py         # Agent routing logic
│   │   └── session_manager.py      # Session state management
│   ├── rag/                        # RAG pipeline
│   │   ├── pipeline.py             # Ingestion orchestrator
│   │   ├── chunker.py              # Text chunking strategies
│   │   ├── embeddings.py           # Embedding generation + caching
│   │   ├── vectorstore.py          # pgvector storage and search
│   │   └── retriever.py            # Context retrieval
│   ├── storage/                    # Database layer
│   │   ├── database.py             # SQLAlchemy async engine + session
│   │   └── models.py               # ORM models (7 tables)
│   ├── evaluation/                 # RAG quality evaluation
│   └── experiments/                # A/B testing framework
├── tests/                          # Test suite
│   ├── conftest.py                 # Shared fixtures
│   ├── test_*.py                   # Unit tests
│   └── integration/                # Integration & E2E tests
├── migrations/                     # Alembic migrations
│   └── versions/                   # Migration files
├── scripts/                        # Utility scripts
│   ├── init_db.py                  # Initialize sample data
│   ├── seed_knowledge_base.py      # Seed RAG knowledge base
│   └── run_evaluation.py           # Run RAG evaluation
├── frontend/                       # Chat UI (HTML/JS)
│   ├── index.html                  # Landing page
│   ├── chat.html                   # Chat interface
│   └── serve.py                    # Development server
├── observability/                  # Monitoring config
│   ├── grafana/                    # Grafana dashboards
│   └── prometheus/                 # Prometheus config
├── docs/                           # Documentation
├── docker-compose.yml              # Core services
├── docker-compose.metrics.yml      # Monitoring stack
├── Dockerfile                      # API container
├── requirements.txt                # Python dependencies
├── pytest.ini                      # Test configuration
├── alembic.ini                     # Migration config
└── .env.example                    # Environment template
```

---

## Common Development Tasks

### Database Operations

```bash
# Run migrations
docker-compose exec api alembic upgrade head

# Create a new migration
docker-compose exec api alembic revision --autogenerate -m "description"

# Rollback one migration
docker-compose exec api alembic downgrade -1

# View migration history
docker-compose exec api alembic history

# Reset database (WARNING: destroys all data)
docker-compose down -v
docker-compose up -d

# Seed the knowledge base
docker-compose exec api python scripts/seed_knowledge_base.py

# Initialize sample customer/vehicle data
docker-compose exec api python scripts/init_db.py
```

### Cache Operations

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Clear all cache
docker-compose exec redis redis-cli FLUSHALL

# View cache keys
docker-compose exec redis redis-cli KEYS "genai:*"
```

### Running Tests

```bash
# All tests
docker-compose exec api pytest

# Unit tests only
docker-compose exec api pytest -m unit

# With coverage report
docker-compose exec api pytest --cov=src --cov-report=html

# Specific test file
docker-compose exec api pytest tests/test_pii.py -v
```

### Code Quality

```bash
# Linting
ruff check src/ tests/

# Formatting
black src/ tests/

# Type checking
mypy src/ --ignore-missing-imports
```

---

## Adding New Components

### Adding a New Agent

1. Create the agent directory and file:
   ```
   src/agents/new_agent/
   └── agent.py
   ```

2. Implement the agent class with a `process(state: AgentState) -> str` method

3. Register the agent in `src/orchestrator/graph.py`:
   - Import the agent
   - Add it to the `Orchestrator.__init__` method
   - Create a node method (e.g., `new_agent_node`)
   - Add the node to the workflow
   - Add routing from `classify` to the new node
   - Add edge from new node to `END`

4. Update the classification prompt in `classify_intent` to include the new category

### Adding a New API Endpoint

1. Create or edit a route file in `src/api/routes/`
2. Define the router with `APIRouter()`
3. Add Pydantic models for request/response schemas
4. Include the router in `src/api/main.py`

### Adding a New Document Type

1. Add the type to the document type enum/validation in `src/api/routes/documents.py`
2. Update the chunking strategy selection in `src/rag/chunker.py` if needed
3. Update documentation in `docs/RAG.md`

---

## Debugging

### Log Levels

Set `LOG_LEVEL` in `.env`:

| Level | Use Case |
|-------|----------|
| `DEBUG` | Full detail including LLM prompts and responses |
| `INFO` | Standard operation logs (default) |
| `WARNING` | Only warnings and errors |
| `ERROR` | Only errors |

### Structured Logs

GenAI Auto uses `structlog` for JSON-formatted logs:

```bash
# View API logs
docker-compose logs -f api

# Filter by log level
docker-compose logs api | grep '"level":"error"'

# View specific session
docker-compose logs api | grep '"session_id":"abc123"'
```

### Interactive Debugging

```bash
# Start with reload for development
uvicorn src.api.main:app --reload --log-level debug

# Use Python debugger
# Add in code: import pdb; pdb.set_trace()
# Or use: breakpoint()
```

### Common Issues

| Issue | Solution |
|-------|----------|
| `Model does not exist` | Check `LLM_MODEL` value against OpenRouter models |
| `expected 768 dimensions, not 1536` | `EMBEDDING_DIMENSION` doesn't match model output |
| `Connection refused (postgres)` | Start PostgreSQL: `docker-compose up -d postgres` |
| `Connection refused (redis)` | Start Redis: `docker-compose up -d redis` |
| Maintenance Agent parsing error | Switch to a model with function calling support |
| WebSocket connection drops | Check CORS settings and proxy WebSocket configuration |

---

## Source Files

- Application entry: `src/api/main.py`
- Configuration: `src/api/config.py`
- Test config: `pytest.ini`
- Docker config: `docker-compose.yml`
- Environment template: `.env.example`
