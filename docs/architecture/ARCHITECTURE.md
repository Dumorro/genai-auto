# GenAI Auto - Architecture Documentation

## Overview

GenAI Auto is a multi-agent AI system designed for automotive customer service. It uses LangGraph for orchestration and LangChain for agent implementation.

## System Architecture

```mermaid
graph TB
    subgraph FRONTEND["🖥️ FRONTEND LAYER"]
        UI["Chat UI (Web/Mobile)<br/>- Real-time messaging<br/>- Session management<br/>- Response streaming"]
    end
    
    subgraph API["🔐 API GATEWAY"]
        FastAPI["FastAPI Application<br/>- Authentication & Authorization<br/>- Rate Limiting<br/>- Request Validation<br/>- Response Formatting"]
    end
    
    subgraph ORCHESTRATOR["🤖 ORCHESTRATOR (LangGraph)"]
        StateMachine["State Machine Engine<br/>workflow_engine: v1.2"]
        Intent["Intent<br/>Classification"]
        Routing["Routing<br/>Logic"]
        Context["Context<br/>Management"]
        Fallback["Fallback<br/>Handling"]
        Response["Response<br/>Aggregation"]
        
        Intent --> Routing
        Routing --> Context
        Context --> Response
        Fallback --> Response
    end
    
    subgraph AGENTS["🧠 AGENTS LAYER"]
        subgraph SPECS["Specs Agent (RAG + Manuals)"]
            DocIngest["Document Ingestion<br/>- PDF/DOCX parsing<br/>- Chunking<br/>- Embedding"]
            VectorSearch["Vector Search<br/>- Semantic query<br/>- Similarity score"]
            LLMSynth["LLM Synthesis<br/>- Context injection<br/>- Response generation"]
            
            DocIngest --> VectorSearch
            VectorSearch --> LLMSynth
        end
        
        subgraph MAINT["Maintenance Agent (Tool Call)"]
            ToolCall["Tool Calling Framework<br/>- Scheduling<br/>- Pricing<br/>- History"]
            APIInteg["API Integration<br/>- Scheduler API<br/>- CRM/ERP"]
            Confirm["Confirmation<br/>Handling"]
            
            ToolCall --> APIInteg
            APIInteg --> Confirm
        end
        
        subgraph TROUBLE["Troubleshoot Agent (Diagnostic)"]
            Symptom["Symptom Analysis<br/>- Pattern matching<br/>- Keyword detection"]
            Decision["Decision Logic<br/>- Diagnostic trees<br/>- Severity assessment"]
            Resolution["Resolution Path<br/>- DIY vs Pro<br/>- Safety warnings"]
            
            Symptom --> Decision
            Decision --> Resolution
        end
    end
    
    subgraph STORAGE["💾 STORAGE LAYER"]
        Vector[("PostgreSQL + pgvector<br/>(Vector Store)<br/>- Document embeddings<br/>- Semantic search index<br/>- Metadata storage<br/>Index: IVFFlat<br/>Dimensions: 1536")]
        SQL[("SQL Database<br/>(Customer Data)<br/>- Customer profiles<br/>- Vehicle information<br/>- Service history<br/>- Appointments<br/>- Conversations")]
    end
    
    UI -->|REST/WebSocket<br/>TLS 1.3, OAuth 2.0| FastAPI
    FastAPI --> StateMachine
    StateMachine --> Intent
    
    Routing --> SPECS
    Routing --> MAINT
    Routing --> TROUBLE
    
    VectorSearch -.-> Vector
    LLMSynth --> SQL
    APIInteg -.-> SQL
    Resolution --> SQL
    
    style FRONTEND fill:#e1f5ff
    style API fill:#fff4e1
    style ORCHESTRATOR fill:#ffe1f5
    style AGENTS fill:#f0f0f0
    style SPECS fill:#e1ffe1
    style MAINT fill:#e1ffe1
    style TROUBLE fill:#e1ffe1
    style STORAGE fill:#ffe1e1
    style Vector fill:#ffcccc
    style SQL fill:#ffcccc
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
