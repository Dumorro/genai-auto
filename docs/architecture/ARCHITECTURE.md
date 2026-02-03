# GenAI Auto - Architecture Documentation

## Overview

GenAI Auto is a multi-agent AI system designed for automotive customer service. It uses LangGraph for orchestration and LangChain for agent implementation.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND LAYER                                 │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                        Chat UI (Web/Mobile)                          │   │
│  │  - Real-time messaging                                               │   │
│  │  - Session management                                                │   │
│  │  - Response streaming                                                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ REST/WebSocket
                                      │ TLS 1.3, OAuth 2.0
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              API GATEWAY                                    │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         FastAPI Application                          │   │
│  │  - Authentication & Authorization                                    │   │
│  │  - Rate Limiting                                                     │   │
│  │  - Request Validation                                                │   │
│  │  - Response Formatting                                               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         ORCHESTRATOR (LangGraph)                            │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                       State Machine Engine                           │   │
│  │                                                                       │   │
│  │  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐           │   │
│  │  │    Intent    │───▶│   Routing    │───▶│   Context    │           │   │
│  │  │ Classification│    │    Logic     │    │  Management  │           │   │
│  │  └──────────────┘    └──────────────┘    └──────────────┘           │   │
│  │                                                                       │   │
│  │  ┌──────────────┐    ┌──────────────┐                               │   │
│  │  │   Fallback   │    │   Response   │                               │   │
│  │  │   Handling   │    │  Aggregation │                               │   │
│  │  └──────────────┘    └──────────────┘                               │   │
│  │                                                                       │   │
│  │                    workflow_engine: v1.2                             │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │                 │                 │
                    ▼                 ▼                 ▼
┌─────────────────────────┐ ┌─────────────────────────┐ ┌─────────────────────────┐
│     SPECS AGENT         │ │   MAINTENANCE AGENT     │ │  TROUBLESHOOT AGENT     │
│     (RAG + Manuals)     │ │   (Tool Call/Schedule)  │ │   (Diagnostic Tree)     │
├─────────────────────────┤ ├─────────────────────────┤ ├─────────────────────────┤
│ ┌─────────────────────┐ │ │ ┌─────────────────────┐ │ │ ┌─────────────────────┐ │
│ │ Document Ingestion  │ │ │ │  Tool Calling       │ │ │ │ Symptom Analysis    │ │
│ │ - PDF/DOCX parsing  │ │ │ │  Framework          │ │ │ │ - Pattern matching  │ │
│ │ - Chunking          │ │ │ │  - Scheduling       │ │ │ │ - Keyword detection │ │
│ │ - Embedding         │ │ │ │  - Pricing          │ │ │ └─────────────────────┘ │
│ └─────────────────────┘ │ │ │  - History          │ │ │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │ │ └─────────────────────┘ │ │ │ Decision Logic      │ │
│ │ Vector Search       │ │ │ ┌─────────────────────┐ │ │ │ - Diagnostic trees  │ │
│ │ - Semantic query    │ │ │ │  API Integration    │ │ │ │ - Severity assess.  │ │
│ │ - Similarity score  │ │ │ │  - Scheduler API    │ │ │ └─────────────────────┘ │
│ └─────────────────────┘ │ │ │  - CRM/ERP          │ │ │ ┌─────────────────────┐ │
│ ┌─────────────────────┐ │ │ └─────────────────────┘ │ │ │ Resolution Path     │ │
│ │ LLM Synthesis       │ │ │ ┌─────────────────────┐ │ │ │ - DIY vs Pro        │ │
│ │ - Context injection │ │ │ │  Confirmation       │ │ │ │ - Safety warnings   │ │
│ │ - Response gen.     │ │ │ │  Handling           │ │ │ └─────────────────────┘ │
│ └─────────────────────┘ │ │ └─────────────────────┘ │ │                         │
└─────────────────────────┘ └─────────────────────────┘ └─────────────────────────┘
            │                         │                           │
            │                         │                           │
            └─────────────────────────┼───────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            STORAGE LAYER                                    │
│  ┌─────────────────────────────────┐ ┌─────────────────────────────────┐   │
│  │    PostgreSQL + pgvector        │ │        SQL Database             │   │
│  │    (Vector Store)               │ │        (Customer Data)          │   │
│  │                                 │ │                                 │   │
│  │  - Document embeddings          │ │  - Customer profiles            │   │
│  │  - Semantic search index        │ │  - Vehicle information          │   │
│  │  - Metadata storage             │ │  - Service history              │   │
│  │                                 │ │  - Appointments                 │   │
│  │  Index: IVFFlat                 │ │  - Conversations                │   │
│  │  Dimensions: 1536               │ │                                 │   │
│  └─────────────────────────────────┘ └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow

### Chat Request Flow

1. **User Input** → Frontend captures user message
2. **API Gateway** → Validates, authenticates, rate limits
3. **Orchestrator** → Classifies intent, routes to agent
4. **Agent Processing** → Retrieves context, generates response
5. **Storage** → Logs conversation, updates state
6. **Response** → Streams back through API to frontend

### Document Ingestion Flow

1. **Upload** → Document received via API
2. **Extraction** → Text extracted from PDF/DOCX
3. **Chunking** → Split into 1000-char chunks with overlap
4. **Embedding** → Generate OpenAI embeddings
5. **Storage** → Store in pgvector with metadata

## Agent Details

### Specs Agent (RAG + Manuals)
- Uses RAG (Retrieval Augmented Generation)
- Searches technical documentation
- Synthesizes answers from multiple sources

### Maintenance Agent (Tool Call → Scheduler)
- Implements LangChain tools for scheduling
- Integrates with external scheduler API
- Manages appointments and history

### Troubleshoot Agent (Diagnostic Tree)
- Uses decision trees for common issues
- Assesses severity and safety concerns
- Guides users through diagnostic steps

## Security

- TLS 1.3 for all communications
- OAuth 2.0 authentication
- Rate limiting per user/IP
- Input validation and sanitization
- Secure secrets management

## Scalability

- Stateless API design
- Connection pooling for database
- Horizontal scaling with container orchestration
- Async processing throughout
