# GenAI Auto - Documentation Index

Complete documentation for the GenAI Auto multi-agent AI system for automotive customer service.

---

## Getting Started

| Document | Description |
|----------|-------------|
| [README](../README.md) | Project overview, features, and quick start |
| [Quick Start Guide](../QUICKSTART.md) | 5-minute setup guide |
| [Architecture](architecture/ARCHITECTURE.md) | System architecture and data flows |
| [Contributing](../CONTRIBUTING.md) | Contribution guidelines and code style |

## Core Concepts

| Document | Description |
|----------|-------------|
| [Multi-Agent System](AGENTS.md) | Agent capabilities, orchestration, and human handoff |
| [RAG Pipeline](RAG.md) | Document ingestion, chunking, embeddings, and retrieval |
| [API Reference](API.md) | Complete REST and WebSocket API documentation |

## Production Features

| Document | Description |
|----------|-------------|
| [Essential Metrics](METRICS.md) | 5 core metrics: tokens, cost, latency, errors, feedback |
| [Advanced Metrics](ADVANCED_METRICS.md) | 5 advanced metrics: RAG quality, cache, handoff, completion, routing |
| [A/B Testing](AB_TESTING.md) | Experiment framework with statistical significance testing |
| [ML Observability](ML_OBSERVABILITY.md) | Model drift detection and performance monitoring |
| [Alerting](ALERTING.md) | Alertmanager setup with Slack, Email, PagerDuty |
| [WebSocket Chat](WEBSOCKET.md) | Real-time streaming chat protocol and client examples |

## Operations

| Document | Description |
|----------|-------------|
| [Deployment Guide](DEPLOYMENT.md) | Docker deployment, reverse proxy, TLS, scaling |
| [Security](SECURITY.md) | Authentication, PII masking, production hardening |
| [Development Guide](DEVELOPMENT.md) | Local setup, project structure, debugging, testing |
| [Testing & Evaluation](EVALUATION.md) | Test suite, CI/CD, quality gates |

## Reference

| Document | Description |
|----------|-------------|
| [Environment Variables](ENV_VARIABLES.md) | Complete configuration reference |
| [Database Schema](DATABASE.md) | ER diagram, table schemas, migrations |
| [Changelog](../CHANGELOG.md) | Version history and migration guides |
| [License](../LICENSE) | MIT License |

## Reports

| Document | Description |
|----------|-------------|
| [E2E Test Report](reports/E2E_TEST_REPORT.md) | End-to-end test results (15/15 passing) |
| [Deployment Log](reports/DEPLOYMENT_LOG.md) | Deployment history and issues resolved |
| [WebSocket Report](reports/WEBSOCKET_REPORT.md) | WebSocket feature implementation details |
| [Bug Fixes](reports/bugfixes/) | Detailed bug fix analyses |

---

## Quick Links

- **Interactive API Docs**: http://localhost:8000/docs (when running)
- **Chat Interface**: http://localhost:8000/chat
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **GitHub Issues**: [github.com/Dumorro/genai-auto/issues](https://github.com/Dumorro/genai-auto/issues)
