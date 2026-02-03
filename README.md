# GenAI Auto 🚗

Sistema multi-agente de IA para atendimento ao cliente automotivo - desenvolvido para montadoras de veículos.

## Stack

| Componente | Tecnologia | Descrição |
|------------|------------|-----------|
| **LLM** | OpenRouter | Modelos gratuitos (Llama 3.1, Gemma, Mistral) |
| **Embeddings** | OpenRouter | nomic-embed-text-v1.5 |
| **Vector DB** | PostgreSQL + pgvector | Armazenamento e busca vetorial |
| **Cache** | Redis | Cache de respostas e embeddings |
| **API** | FastAPI | REST API com OpenAPI docs |
| **Auth** | JWT built-in | Autenticação leve sem serviço externo |

## Arquitetura

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────────────────────┐
│  Frontend   │────▶│ API Gateway │────▶│      Orchestrator (LangGraph)    │
│  (Chat UI)  │     │  FastAPI    │     │         State Machine            │
└─────────────┘     └─────────────┘     └──────────────┬───────────────────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────────────────────┐
                    │                                  │                                  │
                    ▼                                  ▼                                  ▼
        ┌───────────────────┐          ┌───────────────────────┐          ┌───────────────────────┐
        │  Agent: Specs     │          │  Agent: Maintenance   │          │  Agent: Troubleshoot  │
        │  (RAG + Manuais)  │          │  (Agendamento)        │          │  (Diagnóstico)        │
        └─────────┬─────────┘          └───────────────────────┘          └───────────────────────┘
                  │
                  ▼
        ┌───────────────────┐
        │   RAG Pipeline    │
        │  ┌─────────────┐  │
        │  │  Chunker    │  │
        │  │  Embeddings │  │
        │  │  VectorStore│  │
        │  └─────────────┘  │
        └─────────┬─────────┘
                  │
                  ▼
        ┌───────────────────┐
        │ PostgreSQL        │
        │ + pgvector        │
        └───────────────────┘
```

## Agentes

| Agente | Função | Capabilities |
|--------|--------|--------------|
| **Specs** | Documentação técnica | RAG sobre manuais, specs, FAQs |
| **Maintenance** | Agendamento | Marcar revisões, consultar histórico |
| **Troubleshoot** | Diagnóstico | Árvore de decisão, análise de sintomas |

## Quick Start

### 1. Clone e configure

```bash
git clone https://github.com/thebotjarvison/genai-auto.git
cd genai-auto

# Copiar configuração
cp .env.example .env

# Editar .env com sua chave OpenRouter
# OPENROUTER_API_KEY=sk-or-v1-xxx
# JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 2. Suba os containers

```bash
docker-compose up -d
```

### 3. Popule a base de conhecimento

```bash
docker-compose exec api python scripts/seed_knowledge_base.py
```

### 4. Acesse a API

- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **PGAdmin** (opcional): http://localhost:5050

## API Endpoints

### Autenticação

```bash
# Registrar usuário
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "senha123", "name": "João"}'

# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "senha123"}'

# Resposta: { "access_token": "xxx", "refresh_token": "xxx" }
```

### Chat

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message": "Qual a potência do motor do GenAuto X1?"}'
```

### RAG - Base de Conhecimento

```bash
# Upload de documento
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@manual.pdf" \
  -F "document_type=manual"

# Ingerir texto
curl -X POST http://localhost:8000/api/v1/documents/ingest-text \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Conteúdo do documento...",
    "source": "nome_do_documento",
    "document_type": "manual"
  }'

# Busca semântica
curl -X POST http://localhost:8000/api/v1/documents/search \
  -H "Content-Type: application/json" \
  -d '{"query": "como trocar óleo", "top_k": 5}'

# Listar documentos
curl -X GET http://localhost:8000/api/v1/documents \
  -H "Authorization: Bearer <token>"

# Estatísticas
curl -X GET http://localhost:8000/api/v1/documents/stats

# Deletar documento
curl -X DELETE http://localhost:8000/api/v1/documents/manual.pdf \
  -H "Authorization: Bearer <token>"
```

## RAG Pipeline

### Formatos Suportados
- PDF (`.pdf`)
- Word (`.docx`)
- Texto (`.txt`)
- Markdown (`.md`)

### Estratégias de Chunking
- `recursive` - Padrão, respeita limites de sentença
- `semantic` - Baseado em parágrafos
- `markdown` - Respeita estrutura de headers
- `fixed` - Tamanho fixo

### Tipos de Documento
- `manual` - Manuais do proprietário
- `spec` - Especificações técnicas
- `guide` - Guias de recursos
- `faq` - Perguntas frequentes
- `troubleshoot` - Diagnóstico e problemas

## Features de Produção

### 🔒 Segurança
- **JWT Auth**: Autenticação stateless com refresh tokens
- **PII Masking**: Máscara automática de CPF, CNPJ, VIN, placas em logs
- **Rate Limiting**: Proteção contra abuso

### 📊 Observabilidade
- **Request Tracing**: X-Request-ID em todas as requisições
- **Token Usage**: Monitoramento de consumo de tokens
- **Metrics**: `/api/v1/metrics` para monitoramento

### 👋 Human Handoff
- **Confidence Threshold**: Escala para humano se confiança < 70%
- **Detecção de Intent**: Reconhece pedidos de atendimento humano
- **Safety Detection**: Prioriza questões de segurança

### ⚡ Performance
- **Response Cache**: Redis cache para respostas frequentes
- **Embedding Cache**: Cache de embeddings para queries repetidas
- **Connection Pooling**: Pool de conexões PostgreSQL

## Configuração

### Variáveis de Ambiente

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

### Modelos Gratuitos (OpenRouter)

| Modelo | ID |
|--------|-----|
| Llama 3.1 8B | `meta-llama/llama-3.1-8b-instruct:free` |
| Gemma 2 9B | `google/gemma-2-9b-it:free` |
| Mistral 7B | `mistralai/mistral-7b-instruct:free` |
| Qwen 2 7B | `qwen/qwen-2-7b-instruct:free` |

## Estrutura do Projeto

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

## Desenvolvimento

### Rodar localmente

```bash
# Instalar dependências
pip install -r requirements.txt

# Subir apenas DB e Redis
docker-compose up -d postgres redis

# Rodar API
uvicorn src.api.main:app --reload
```

### Testes

```bash
pytest tests/ -v
```

## License

MIT License - veja [LICENSE](LICENSE) para detalhes.

---

**GenAI Auto** | Sistema Multi-Agente para Atendimento Automotivo
