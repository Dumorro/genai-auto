# GenAI Auto 🚗

Multi-agent AI system for automotive customer service - designed for vehicle manufacturers.

## Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **LLM** | OpenRouter | Free models (Llama 3.1, Gemma, Mistral) |
| **Embeddings** | OpenRouter | nomic-embed-text-v1.5 |
| **Vector DB** | PostgreSQL + pgvector | Vector storage and search |
| **Cache** | Redis | Response and embedding cache |
| **API** | FastAPI | REST API with OpenAPI docs |
| **Auth** | JWT built-in | Lightweight auth, no external service |

## Architecture

```mermaid
graph TD
    A[Frontend<br/>Chat UI] --> B[API Gateway<br/>FastAPI]
    B --> C[Orchestrator<br/>LangGraph State Machine]
    
    C --> D[Agent: Specs<br/>RAG + Manuals]
    C --> E[Agent: Maintenance<br/>Scheduling]
    C --> F[Agent: Troubleshoot<br/>Diagnostics]
    
    D --> G[RAG Pipeline]
    G --> H[Chunker]
    G --> I[Embeddings]
    G --> J[VectorStore]
    
    J --> K[(PostgreSQL<br/>+ pgvector)]
    
    B -.-> L[(Redis<br/>Cache)]
    
    style A fill:#e1f5ff
    style B fill:#fff4e1
    style C fill:#ffe1f5
    style D fill:#e1ffe1
    style E fill:#e1ffe1
    style F fill:#e1ffe1
    style G fill:#f5e1ff
    style K fill:#ffe1e1
    style L fill:#ffe1e1
```

## Agents

| Agent | Function | Capabilities |
|-------|----------|--------------|
| **Specs** | Technical documentation | RAG over manuals, specs, FAQs |
| **Maintenance** | Scheduling | Book services, check history |
| **Troubleshoot** | Diagnostics | Decision tree, symptom analysis |

## Quick Start

### 1. Clone and configure

```bash
git clone https://github.com/thebotjarvison/genai-auto.git
cd genai-auto

# Copy configuration
cp .env.example .env

# Edit .env with your OpenRouter key
# OPENROUTER_API_KEY=sk-or-v1-xxx
# JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Start containers

```bash
docker-compose up -d
```

### 3. Seed the knowledge base

```bash
docker-compose exec api python scripts/seed_knowledge_base.py
```

### 4. Access the API

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **PGAdmin** (optional): http://localhost:5050

## API Endpoints

### Authentication

```bash
# Register user
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123", "name": "John"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password123"}'

# Response: { "access_token": "xxx", "refresh_token": "xxx" }
```

### Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the engine power of the GenAuto X1?"}'
```

### RAG - Knowledge Base

```bash
# Upload document
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@manual.pdf" \
  -F "document_type=manual"

# Ingest text
curl -X POST http://localhost:8000/api/v1/documents/ingest-text \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Document content...",
    "source": "document_name",
    "document_type": "manual"
  }'

# Semantic search
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "how to change oil", "top_k": 5}'

# List documents
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <token>"

# Statistics
curl -X GET http://localhost:8000/api/v1/documents/stats

# Delete document
curl -X DELETE http://localhost:8000/api/v1/documents/manual.pdf \
  -H "Authorization: Bearer <token>"
```

## RAG Pipeline

### Supported Formats
- PDF (`.pdf`)
- Word (`.docx`)
- Text (`.txt`)
- Markdown (`.md`)

### Chunking Strategies
- `recursive` - Default, respects sentence boundaries
- `semantic` - Paragraph-based
- `markdown` - Respects header structure
- `fixed` - Fixed size chunks

### Document Types
- `manual` - Owner manuals
- `spec` - Technical specifications
- `guide` - Feature guides
- `faq` - Frequently asked questions
- `troubleshoot` - Diagnostics and problems

## Production Features

### 🔒 Security
- **JWT Auth**: Stateless authentication with refresh tokens
- **PII Masking**: Auto-mask SSN, VIN, license plates in logs
- **Rate Limiting**: Abuse protection

### 📊 Observability
- **Request Tracing**: X-Request-ID on all requests
- **Token Usage**: Token consumption monitoring
- **Metrics**: `/api/v1/metrics` for monitoring

### 👋 Human Handoff
- **Confidence Threshold**: Escalate to human if confidence < 70%
- **Intent Detection**: Recognizes human assistance requests
- **Safety Detection**: Prioritizes safety-related issues

### ⚡ Performance
- **Response Cache**: Redis cache for frequent responses
- **Embedding Cache**: Cache embeddings for repeated queries
- **Connection Pooling**: PostgreSQL connection pool

## Configuration

### Environment Variables

```bash
# LLM (OpenRouter)
OPENROUTER_API_KEY=sk-or-v1-xxx
LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5

# Database
DATABASE_URL=postgresql://genai:secret@postgres:5432/genai_auto

# Auth
JWT_SECRET_KEY=your-secret-key-here
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# Cache
REDIS_URL=redis://redis:6379
CACHE_ENABLED=true
CACHE_TTL=3600

# Human Handoff
CONFIDENCE_THRESHOLD=0.7
HUMAN_SUPPORT_WEBHOOK=https://your-webhook.com

# Security
MASK_PII=true
```

### Free Models (OpenRouter)

| Model | ID |
|-------|-----|
| Llama 3.1 8B | `meta-llama/llama-3.1-8b-instruct:free` |
| Gemma 2 9B | `google/gemma-2-9b-it:free` |
| Mistral 7B | `mistralai/mistral-7b-instruct:free` |
| Qwen 2 7B | `qwen/qwen-2-7b-instruct:free` |

## Project Structure

```
genai-auto/
├── src/
│   ├── api/                 # FastAPI application
│   │   ├── auth/            # JWT authentication
│   │   ├── routes/          # API endpoints
│   │   ├── cache.py         # Redis caching
│   │   ├── handoff.py       # Human handoff
│   │   ├── observability.py # Tracing & metrics
│   │   └── pii.py           # PII protection
│   ├── agents/              # LangGraph agents
│   │   ├── specs/           # RAG + documentation
│   │   ├── maintenance/     # Scheduling
│   │   └── troubleshoot/    # Diagnostics
│   ├── orchestrator/        # LangGraph state machine
│   ├── rag/                 # RAG pipeline
│   │   ├── pipeline.py      # Main orchestrator
│   │   ├── chunker.py       # Document chunking
│   │   ├── embeddings.py    # Embedding service
│   │   └── vectorstore.py   # pgvector operations
│   └── storage/             # Database models
├── scripts/
│   ├── seed_knowledge_base.py  # Populate sample data
│   └── init_postgres.sql       # Database schema
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## Development

### Run locally

```bash
# Install dependencies
pip install -r requirements.txt

# Start only DB and Redis
docker-compose up -d postgres redis

# Run API
uvicorn src.api.main:app --reload
```

### Tests

```bash
pytest tests/ -v
```

## License

MIT License - see [LICENSE](LICENSE) for details.

---

**GenAI Auto** | Multi-Agent System for Automotive Customer Service
