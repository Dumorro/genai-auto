# Testing & Evaluation

## Overview

GenAI Auto includes a comprehensive testing framework covering unit tests, integration tests, end-to-end tests, and RAG quality evaluation.

---

## Test Structure

```
tests/
├── conftest.py                         # Shared fixtures (db engine, session, settings)
├── __init__.py
├── test_api.py                         # API endpoint tests
├── test_auth.py                        # Authentication tests
├── test_pii.py                         # PII masking tests
├── test_rag.py                         # RAG pipeline tests
├── test_evaluation.py                  # Evaluation framework tests
└── integration/
    ├── test_e2e_flow.py               # Full end-to-end flow
    ├── test_full_chat_flow.py         # Chat conversation flows
    ├── test_frontend_integration.py   # Frontend serving tests
    └── test_websocket.py             # WebSocket tests
```

---

## Test Markers

Custom markers defined in `pytest.ini`:

| Marker | Description | Example Usage |
|--------|-------------|---------------|
| `unit` | Fast tests, no external dependencies | `pytest -m unit` |
| `integration` | Requires database, Redis, etc. | `pytest -m integration` |
| `e2e` | Full system end-to-end tests | `pytest -m e2e` |
| `slow` | Tests taking >1s | `pytest -m "not slow"` |
| `websocket` | WebSocket-specific tests | `pytest -m websocket` |
| `auth` | Authentication tests | `pytest -m auth` |
| `rag` | RAG/vector store tests | `pytest -m rag` |
| `agents` | Agent-specific tests | `pytest -m agents` |

---

## Running Tests

### All Tests

```bash
# Run all tests with coverage
pytest

# Verbose output
pytest -v
```

### By Marker

```bash
# Unit tests only (fast, no external deps)
pytest -m unit

# Integration tests (requires running services)
pytest -m integration

# Skip slow tests
pytest -m "not slow"

# WebSocket tests only
pytest -m websocket
```

### By File or Directory

```bash
# Single test file
pytest tests/test_pii.py

# Integration tests directory
pytest tests/integration/

# Specific test function
pytest tests/test_pii.py::test_mask_email
```

### With Docker

```bash
# Run tests inside the Docker container
docker-compose exec api pytest

# Run specific markers
docker-compose exec api pytest -m unit

# Run with coverage
docker-compose exec api pytest --cov=src --cov-report=html
```

---

## Coverage

Coverage is configured in `pytest.ini` with these defaults:

| Setting | Value |
|---------|-------|
| Source | `src/` |
| Report formats | terminal, HTML (`htmlcov/`), XML (`coverage.xml`) |
| Excluded | tests, conftest, `__init__`, migrations |
| Excluded patterns | `pragma: no cover`, `__repr__`, `NotImplementedError` |

```bash
# View coverage report
pytest --cov=src --cov-report=term-missing

# Generate HTML report
pytest --cov=src --cov-report=html
open htmlcov/index.html
```

---

## RAG Evaluation

### Overview

The evaluation framework (`src/evaluation/`) measures RAG pipeline quality across retrieval and generation metrics.

### Evaluation Script

```bash
# Run the evaluation script
docker-compose exec api python scripts/run_evaluation.py
```

### API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/evaluation/single` | POST | Evaluate a single query |
| `/api/v1/evaluation/batch` | POST | Run batch evaluation |
| `/api/v1/evaluation/custom` | POST | Evaluate custom test cases |
| `/api/v1/evaluation/status/{name}` | GET | Check evaluation status |
| `/api/v1/evaluation/results/{name}` | GET | Get evaluation results |
| `/api/v1/evaluation/results/{name}/summary` | GET | Get results summary |
| `/api/v1/evaluation/list` | GET | List all evaluations |
| `/api/v1/evaluation/sample-dataset` | GET | Get sample test dataset |

All evaluation endpoints require authentication.

### Metrics Measured

**Retrieval Metrics**:

| Metric | Description |
|--------|-------------|
| Precision | Fraction of retrieved chunks that are relevant |
| Recall | Fraction of relevant chunks that were retrieved |
| MRR | Mean Reciprocal Rank of first relevant result |

**Generation Metrics**:

| Metric | Description |
|--------|-------------|
| Faithfulness | How well the response aligns with retrieved context |
| Relevance | How relevant the response is to the query |
| Correctness | Accuracy compared to expected answer |

**Latency Metrics**:

| Metric | Description |
|--------|-------------|
| Retrieval (ms) | Time to search the vector store |
| Generation (ms) | Time for LLM to generate response |
| Total (ms) | End-to-end latency |

### Sample Evaluation

```bash
# Evaluate a single query
curl -X POST http://localhost:8000/api/v1/evaluation/single \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What engine does the GenAuto X1 have?",
    "expected_answer": "1.5L turbocharged engine producing 150 HP",
    "k": 5
  }'

# Run batch evaluation with sample dataset
curl -X POST http://localhost:8000/api/v1/evaluation/batch \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "weekly-eval", "use_sample_dataset": true}'
```

---

## CI/CD Pipeline

### GitHub Actions Workflows

#### 1. CI/CD Pipeline (`ci.yml`)

Triggered on push to `main`/`develop` and PRs to `main`.

| Job | Description | Dependencies |
|-----|-------------|--------------|
| `lint` | Ruff linting, MyPy type checking | None |
| `test-unit` | Unit tests (Python 3.10, 3.11 matrix) | lint |
| `test-e2e` | E2E tests with PostgreSQL + Redis services | lint |
| `test-frontend` | Frontend file validation and server test | lint |
| `security` | Safety (deps) + Bandit (code) scans | lint |
| `build` | Docker image build and test | test-unit, test-e2e, test-frontend |
| `deploy` | Push to GHCR (main branch only) | build |
| `report` | CI summary report | all tests |

**Services provisioned for E2E**:
- `pgvector/pgvector:pg16` (PostgreSQL + pgvector)
- `redis:7-alpine`

#### 2. PR Check (`pr-check.yml`)

Fast checks on pull request open/sync:

| Check | Description |
|-------|-------------|
| Ruff | Linting |
| Black | Code formatting |
| File sizes | Warn on files >5MB |
| Secrets scan | Detect hardcoded credentials |
| PR size | Warn on >50 files or >500 lines |

#### 3. Format (`format.yml`)

Auto-formatting workflow.

#### 4. Release (`release.yml`)

Release management workflow.

---

## Quality Gates

### Pre-Commit (Local)

```bash
# Install pre-commit hooks
pip install ruff black mypy

# Run manually
ruff check src/ tests/
black --check src/ tests/
mypy src/ --ignore-missing-imports
```

### Pre-Merge (CI)

The following must pass before merging a PR:

1. Ruff linting (no errors)
2. Black formatting (no differences)
3. No hardcoded secrets
4. Unit tests pass
5. E2E tests pass (with services)
6. Docker image builds successfully

### Pre-Deploy (Production)

Additional gates for production deployment:

1. All CI jobs pass
2. Branch is `main`
3. Event is `push` (not PR)
4. Environment approval (GitHub Environments)

---

## Test Fixtures

Shared fixtures in `tests/conftest.py`:

| Fixture | Scope | Description |
|---------|-------|-------------|
| `event_loop` | session | Async event loop for tests |
| `settings` | session | Application settings instance |
| `db_engine` | session | SQLAlchemy async engine |
| `db_session` | function | Database session (auto-rollback) |

---

## Troubleshooting Tests

### Database Connection Errors

```
Error: connection refused (localhost:5432)
```

**Fix**: Ensure PostgreSQL is running:
```bash
docker-compose up -d postgres
```

### Async Test Failures

```
Error: no running event loop
```

**Fix**: Ensure `--asyncio-mode=auto` is set in `pytest.ini` (already configured).

### Coverage Too Low

If coverage drops below threshold, check:
1. New code has tests
2. Tests actually exercise the code paths
3. Coverage exclusions in `pytest.ini` are reasonable

---

## Source Files

- Test configuration: `pytest.ini`
- Test fixtures: `tests/conftest.py`
- Evaluation script: `scripts/run_evaluation.py`
- CI pipeline: `.github/workflows/ci.yml`
- PR checks: `.github/workflows/pr-check.yml`
- E2E test report: `docs/reports/E2E_TEST_REPORT.md`
