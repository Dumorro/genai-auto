# GenAI Auto 🚗

Multi-agent AI system for automotive customer service - designed for vehicle manufacturers/assemblers.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────────────────────────────┐
│  Frontend   │────▶│ API Gateway │────▶│      Orchestrator (LangGraph)    │
│  (Chat UI)  │     │ REST/Auth   │     │  ┌────────────────────────────┐  │
└─────────────┘     └─────────────┘     │  │ State Machine / Routing    │  │
                                        │  └────────────────────────────┘  │
                                        └──────────────┬───────────────────┘
                                                       │
                    ┌──────────────────────────────────┼──────────────────────────────────┐
                    │                                  │                                  │
                    ▼                                  ▼                                  ▼
        ┌───────────────────┐          ┌───────────────────────┐          ┌───────────────────────┐
        │  Agent: Specs     │          │  Agent: Maintenance   │          │  Agent: Troubleshoot  │
        │  (RAG + Manuals)  │          │  (Tool Call/Schedule) │          │  (Diagnostic Tree)    │
        └─────────┬─────────┘          └───────────┬───────────┘          └───────────┬───────────┘
                  │                                │                                  │
                  └────────────────────────────────┼──────────────────────────────────┘
                                                   │
                                                   ▼
                              ┌─────────────────────────────────────────┐
                              │            Storage Layer                │
                              │  ┌─────────────────┐ ┌───────────────┐  │
                              │  │ PostgreSQL +    │ │ Customer DB   │  │
                              │  │ pgvector (RAG)  │ │ (Profiles)    │  │
                              │  └─────────────────┘ └───────────────┘  │
                              └─────────────────────────────────────────┘
```

## Tech Stack

- **Framework**: LangChain + LangGraph
- **Database**: PostgreSQL with pgvector extension
- **API**: FastAPI (REST)
- **Containers**: Docker + Docker Compose
- **LLM**: OpenAI GPT-4 (configurable)

## Agents

### 1. Specs Agent (RAG + Manuals)
- Document ingestion pipeline
- Vector search for technical manuals
- LLM synthesis for user queries

### 2. Maintenance Agent (Tool Call → Scheduler)
- API integration with scheduling systems
- Appointment booking and confirmation
- Service reminders

### 3. Troubleshooting Agent (Diagnostic Tree)
- Symptom analysis
- Decision logic trees
- Resolution path recommendations

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- OpenAI API Key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/your-username/genai-auto.git
cd genai-auto
```

2. Copy environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys
```

3. Start the containers:
```bash
docker-compose up -d
```

4. Initialize the database:
```bash
docker-compose exec api python scripts/init_db.py
```

5. Access the API:
- API: http://localhost:8000
- Docs: http://localhost:8000/docs

## Project Structure

```
genai-auto/
├── src/
│   ├── api/              # FastAPI application
│   ├── agents/           # LangGraph agents
│   │   ├── specs/        # RAG + Manuals agent
│   │   ├── maintenance/  # Scheduling agent
│   │   └── troubleshoot/ # Diagnostic agent
│   ├── orchestrator/     # LangGraph state machine
│   ├── storage/          # Database models & repositories
│   └── frontend/         # Chat UI (optional)
├── docs/
│   ├── specs/            # Technical specifications
│   └── architecture/     # Architecture diagrams
├── tests/                # Test suite
├── scripts/              # Utility scripts
├── docker-compose.yml    # Container orchestration
└── requirements.txt      # Python dependencies
```

## License

MIT License - See [LICENSE](LICENSE) for details.

---

**Project GenAI Auto** | Rev 1.4 | 2024
