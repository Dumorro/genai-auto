# GenAI Auto 🚗

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![LangChain](https://img.shields.io/badge/LangChain-0.3+-purple.svg)](https://www.langchain.com/)
[![Prometheus](https://img.shields.io/badge/Prometheus-Metrics-orange.svg)](https://prometheus.io/)

Multi-agent AI system for automotive customer service - designed for vehicle manufacturers.

**Key Features:**
- 🤖 Multi-agent architecture (Specs, Maintenance, Troubleshoot)
- 📚 RAG pipeline with pgvector
- 💬 Real-time WebSocket chat with streaming responses
- 📊 Production-ready metrics (Prometheus + Grafana)
- 🔐 JWT authentication
- ⚡ Redis caching
- 🚀 Docker-ready deployment

## Table of Contents

- [Features](#features)
- [Stack](#stack)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [API Endpoints](#api-endpoints)
- [Production Features](#production-features)
- [Monitoring & Metrics](#monitoring--metrics)
- [Configuration](#configuration)
- [Development](#development)
- [License](#license)

## Features

### 🤖 Multi-Agent System
- **Specs Agent**: RAG-powered technical documentation search
- **Maintenance Agent**: Service scheduling and history
- **Troubleshoot Agent**: Diagnostic decision trees

### 📊 Production-Ready Monitoring
- **5 Essential Metrics**: Token usage, cost, latency, errors, feedback
- **Prometheus Integration**: Ready for scraping
- **Grafana Dashboards**: Pre-configured queries
- **15 Alerts**: Cost, latency, errors, satisfaction
- **Real-time Cost Tracking**: LLM cost per request

### 📚 Advanced RAG Pipeline
- **Multiple Formats**: PDF, DOCX, TXT, Markdown
- **Semantic Search**: pgvector similarity search
- **Smart Chunking**: Recursive, semantic, markdown strategies
- **Embedding Cache**: Redis-backed for performance

### 🔐 Enterprise Security
- **JWT Authentication**: Stateless, secure
- **PII Masking**: Auto-mask sensitive data in logs
- **Rate Limiting**: Abuse protection
- **Input Validation**: Strict schema enforcement

### ⚡ Performance
- **Response Caching**: Redis cache for frequent queries
- **Connection Pooling**: Optimized database connections
- **Async Everywhere**: Full async/await support
- **Human Handoff**: Automatic escalation when confidence < 70%

### 💬 Real-Time Chat Interface
- **WebSocket Streaming**: Live bi-directional communication
- **Progress Updates**: Real-time feedback on RAG retrieval, agent routing, generation
- **Mobile-First UI**: Responsive design with iOS-style blur effects
- **Smart Message Rendering**: Streaming token display with typing indicators
- **Agent Attribution**: Shows which specialist handled each request
- **No Authentication Required**: PoC-ready for immediate testing

## Stack

| Component | Technology | Description |
|-----------|------------|-------------|
| **LLM** | OpenRouter | Free models (Llama 3.1, Gemma, Mistral) |
| **Embeddings** | OpenRouter | nomic-embed-text-v1.5 |
| **Vector DB** | PostgreSQL + pgvector | Vector storage and search |
| **Cache** | Redis | Response and embedding cache |
| **API** | FastAPI | REST API with OpenAPI docs |
| **Auth** | JWT built-in | Lightweight auth, no external service |
| **Metrics** | Prometheus | Production metrics tracking |

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
    
    style A fill:#4A90E2,stroke:#2E5C8A,stroke-width:3px,color:#fff
    style B fill:#F5A623,stroke:#C77D1A,stroke-width:3px,color:#000
    style C fill:#BD10E0,stroke:#8A0CAA,stroke-width:3px,color:#fff
    style D fill:#7ED321,stroke:#5FA319,stroke-width:3px,color:#000
    style E fill:#7ED321,stroke:#5FA319,stroke-width:3px,color:#000
    style F fill:#7ED321,stroke:#5FA319,stroke-width:3px,color:#000
    style G fill:#9013FE,stroke:#6B0EBE,stroke-width:3px,color:#fff
    style H fill:#9013FE,stroke:#6B0EBE,stroke-width:2px,color:#fff
    style I fill:#9013FE,stroke:#6B0EBE,stroke-width:2px,color:#fff
    style J fill:#9013FE,stroke:#6B0EBE,stroke-width:2px,color:#fff
    style K fill:#D0021B,stroke:#9A0114,stroke-width:3px,color:#fff
    style L fill:#D0021B,stroke:#9A0114,stroke-width:3px,color:#fff
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
git clone https://github.com/Dumorro/genai-auto.git
cd genai-auto

# Copy configuration
cp .env.example .env

# Edit .env with your OpenRouter key
# OPENROUTER_API_KEY=sk-or-v1-xxx
# JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Start containers

**Basic setup (API + Database + Redis):**
```bash
docker-compose up -d
```

**With monitoring (+ Prometheus + Grafana):**
```bash
docker-compose -f docker-compose.yml -f docker-compose.metrics.yml up -d
```

### 3. Seed the knowledge base

```bash
docker-compose exec api python scripts/seed_knowledge_base.py
```

### 4. Access the Chat Interface

**Web UI (Recommended):**
```
http://localhost:8000/chat
```

**Features:**
- Real-time WebSocket streaming
- Mobile-responsive design
- Progress indicators (RAG retrieval, agent routing)
- Agent attribution badges
- No authentication required (PoC mode)

**Test Page:**
```
http://localhost:8000/ws/test
```
Simple test interface for debugging WebSocket connections.

### 4. Access the services

**Core:**
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PGAdmin** (optional): http://localhost:5050

**Monitoring (if enabled):**
- **Metrics Endpoint**: http://localhost:8000/api/v1/metrics
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/admin)

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

**REST API (with auth):**
```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the engine power of the GenAuto X1?"}'
```

**WebSocket (real-time, no auth):**
```javascript
// Connect to WebSocket
const ws = new WebSocket('ws://localhost:8000/ws/chat');

// Send message
ws.send(JSON.stringify({
  type: 'message',
  message: 'What are the specs of a Honda Civic 2024?',
  session_id: 'my-session-123'
}));

// Receive messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: 'progress' | 'token' | 'complete' | 'error'
};
```

**Access Web UI:**
- Main chat: `http://localhost:8000/chat`
- Test page: `http://localhost:8000/ws/test`

### Metrics & Feedback

```bash
# Get Prometheus metrics
curl http://localhost:8000/api/v1/metrics

# Submit user feedback (thumbs up/down)
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_123",
    "sentiment": "positive",
    "comment": "Very helpful!"
  }'

# Metrics summary
curl http://localhost:8000/api/v1/metrics/summary
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

### 📊 Metrics & Observability
- **10 Production Metrics** (Prometheus-ready):
  
  **Essential (Phase 1):**
  - ✅ **Token Usage** (input/output per agent/model)
  - ✅ **Cost per Request** (real-time LLM cost tracking)
  - ✅ **Response Latency** (P50/P95/P99 distributions)
  - ✅ **Error Rate** (HTTP + LLM errors by type)
  - ✅ **User Feedback** (thumbs up/down tracking)
  
  **Advanced (Phase 2):**
  - ✅ **RAG Similarity Score** (retrieval quality)
  - ✅ **Cache Hit Rate** (performance optimization)
  - ✅ **Handoff Rate** (human escalation tracking)
  - ✅ **Task Completion Rate** (user success)
  - ✅ **Agent Routing Accuracy** (orchestration quality)

- **Prometheus Endpoint**: `/api/v1/metrics`
- **Grafana Dashboards**: Pre-configured queries for visualization
- **25+ Alerts**: Cost, latency, errors, satisfaction, quality
- **Request Tracing**: X-Request-ID on all requests

📖 **[Essential Metrics Guide →](docs/METRICS.md)**  
📖 **[Advanced Metrics Guide →](docs/ADVANCED_METRICS.md)**

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
│   ├── api/                        # FastAPI application
│   │   ├── auth/                   # JWT authentication
│   │   ├── routes/                 # API endpoints
│   │   │   ├── chat_example.py     # Chat with metrics integration
│   │   │   └── metrics_routes.py   # Metrics & feedback endpoints
│   │   ├── cache.py                # Redis caching
│   │   ├── handoff.py              # Human handoff
│   │   ├── metrics.py              # ✨ Prometheus metrics tracking
│   │   ├── observability.py        # Tracing & metrics
│   │   └── pii.py                  # PII protection
│   ├── agents/                     # LangGraph agents
│   │   ├── specs/                  # RAG + documentation
│   │   ├── maintenance/            # Scheduling
│   │   └── troubleshoot/           # Diagnostics
│   ├── orchestrator/               # LangGraph state machine
│   ├── rag/                        # RAG pipeline
│   │   ├── pipeline.py             # Main orchestrator
│   │   ├── chunker.py              # Document chunking
│   │   ├── embeddings.py           # Embedding service
│   │   └── vectorstore.py          # pgvector operations
│   └── storage/                    # Database models
├── docs/
│   ├── architecture/
│   │   └── ARCHITECTURE.md         # Detailed architecture
│   └── METRICS.md                  # ✨ Complete metrics guide
├── scripts/
│   ├── seed_knowledge_base.py      # Populate sample data
│   └── init_postgres.sql           # Database schema
├── docker-compose.yml              # Main services
├── docker-compose.metrics.yml      # ✨ Prometheus + Grafana
├── prometheus.yml                  # ✨ Prometheus config
├── alerts.yml                      # ✨ Alert rules (15 alerts)
├── Dockerfile
└── requirements.txt

✨ = Metrics-related files
```

## Monitoring & Metrics

GenAI Auto includes production-ready metrics tracking powered by Prometheus.

### Available Metrics

| Metric | Description | Use Case |
|--------|-------------|----------|
| **Token Usage** | Input/output tokens per agent/model | Cost forecasting, usage trends |
| **Cost per Request** | Real-time LLM cost in dollars | Budget monitoring, alerts |
| **Response Latency** | P50/P95/P99 distributions | SLA monitoring, performance |
| **Error Rate** | HTTP + LLM errors by type | Incident detection, debugging |
| **User Feedback** | Thumbs up/down tracking | Satisfaction monitoring, A/B testing |

### Quick Queries

**Cost per hour:**
```promql
rate(llm_cost_dollars_total[1h]) * 3600
```

**P95 latency:**
```promql
histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m]))
```

**Error rate %:**
```promql
rate(http_errors_total[5m]) / rate(request_latency_seconds_count[5m]) * 100
```

**User satisfaction %:**
```promql
rate(user_feedback_total{sentiment="positive"}[1h]) / rate(user_feedback_total[1h]) * 100
```

### Pre-configured Alerts

15 alerts included in `alerts.yml`:
- 💰 High/Critical LLM Cost ($10/h, $50/h)
- ⏱️ High/Very High Latency (5s, 10s)
- ❌ High/Critical Error Rate (5%, 20%)
- 😞 Low/Very Low User Satisfaction (60%, 40%)
- 🔥 API Down
- 📊 Too Many Concurrent Requests

### Integration Example

```python
from api.metrics import track_llm_call, track_endpoint_metrics

@track_endpoint_metrics('chat')  # Automatic latency tracking
async def chat(request):
    start = time.time()
    result = await llm.generate(request.message)
    
    track_llm_call(
        model="llama-3.1-8b",
        agent="specs",
        input_tokens=result.usage.input,
        output_tokens=result.usage.output,
        duration=time.time() - start
    )
    
    return result
```

📖 **[Complete Metrics Guide →](docs/METRICS.md)**

---

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

## Documentation

- **[Architecture Guide](docs/architecture/ARCHITECTURE.md)** - Detailed system architecture
- **[Metrics Guide](docs/METRICS.md)** - Complete metrics documentation
- **[API Reference](http://localhost:8000/docs)** - OpenAPI/Swagger docs (when running)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'feat: add some amazing feature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## Roadmap

### Implemented ✅
- [x] ✅ **Production metrics system** (10 metrics: token usage, cost, latency, errors, feedback, RAG similarity, cache hit rate, handoff rate, task completion, routing accuracy)
- [x] ✅ **Grafana dashboard** (20+ panels, auto-provisioning)
- [x] ✅ **Alertmanager** (multi-channel notifications, 25+ alerts)
- [x] ✅ **A/B testing framework** (experiment management, statistical significance)
- [x] ✅ **ML observability** (drift detection, baseline comparison, automated reports)
- [x] ✅ **WebSocket real-time chat** (streaming responses, progress updates, mobile-first UI)

### Planned 🔜
- [ ] Multi-language support (i18n)
- [ ] Voice input/output integration
- [ ] Plugin system for custom agents
- [ ] Knowledge base versioning

## Support

- 📖 **Documentation**: [docs/](docs/)
- 💬 **Issues**: [GitHub Issues](https://github.com/Dumorro/genai-auto/issues)
- 📧 **Email**: tfcoelho@msn.com

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- [LangChain](https://www.langchain.com/) - LLM framework
- [LangGraph](https://langchain-ai.github.io/langgraph/) - Multi-agent orchestration
- [FastAPI](https://fastapi.tiangolo.com/) - Modern API framework
- [Prometheus](https://prometheus.io/) - Metrics and monitoring
- [OpenRouter](https://openrouter.ai/) - LLM API aggregator

---

**GenAI Auto** | Multi-Agent System for Automotive Customer Service

Built with ❤️ by [Thiago Coelho](https://github.com/Dumorro)
