# Changelog

All notable changes to GenAI Auto will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

_No unreleased changes._

## [0.2.0] - 2026-02-09

### Fixed
- **WebSocket Empty Response Bug** (2026-02-09)
  - Fixed critical bug where chat responses were always empty
  - Changed from `workflow.astream()` to `workflow.ainvoke()` 
  - `astream()` returns partial chunks per node; `ainvoke()` returns complete final state
  - Chat interface now correctly displays AI agent responses
  - See `docs/reports/bugfixes/BUGFIX_WEBSOCKET_EMPTY_RESPONSE.md` for detailed analysis

### Added
- 🎯 **Complete Metrics Implementation - 5 Steps** (2026-02-06)
  
  **Step 1: Grafana Dashboard**
  - Complete dashboard with 20+ panels
  - Auto-provisioning (datasource + dashboard)
  - 4 sections: Overview, Essential, Advanced, Performance
  - Real-time updates (30s refresh)
  - Color-coded thresholds
  
  **Step 2: Real Code Integration**
  - RAGRetriever with similarity tracking
  - CacheService with hit/miss tracking
  - SessionManager with task completion
  - AgentRouter with routing accuracy
  - Production-ready implementations
  
  **Step 3: Alertmanager Setup**
  - Multi-channel notifications (Slack, Email, PagerDuty)
  - Smart routing by severity and type
  - Inhibition rules (suppress redundant alerts)
  - Custom notification templates
  - 25+ pre-configured alerts
  
  **Step 4: A/B Testing Framework**
  - Experiment management with variants
  - Consistent user assignment (hashing)
  - Metrics integration (auto-tracking)
  - Statistical significance testing
  - Multi-variant support (A/B/C/...)
  
  **Step 5: ML Observability**
  - Model drift detection (baseline comparison)
  - Performance monitoring (8 key metrics)
  - Automated drift checking
  - Prometheus integration
  - Report generation

- 📊 **Advanced Metrics System (Phase 2)** (2026-02-06)
  - RAG similarity score tracking (retrieval quality)
  - Cache hit rate monitoring (response & embedding caches)
  - Human handoff tracking (escalation reasons & confidence)
  - Task completion rate (completed/abandoned/escalated)
  - Agent routing accuracy (routing confidence & rerouting)
  - 10 new alert rules for advanced metrics
  - Complete advanced metrics documentation (`docs/ADVANCED_METRICS.md`)
  - Integration examples (`src/api/routes/advanced_metrics_example.py`)
  - Helper functions for easy tracking

- 📊 **Essential Metrics System** (2026-02-06)
  - Token usage tracking (input/output per agent/model)
  - Real-time cost calculation per request
  - Response latency histograms (P50/P95/P99)
  - Error rate tracking (HTTP + LLM errors)
  - User feedback API (thumbs up/down)
  - Prometheus endpoint at `/api/v1/metrics`
  - 15 pre-configured alerts (cost, latency, errors, satisfaction)
  - Grafana dashboard queries
  - Complete metrics documentation (`docs/METRICS.md`)
  - Docker Compose setup for Prometheus + Grafana
  - Integration examples and best practices

- 🎨 **Documentation Improvements** (2026-02-06)
  - Mermaid diagrams for architecture (dark mode optimized)
  - Detailed architecture documentation
  - Table of contents in README
  - Feature highlights section
  - Badges for technologies
  - Contributing guidelines
  - Roadmap section
  - Acknowledgments

### Changed
- Updated README with comprehensive project overview
- Enhanced project structure documentation
- Improved Quick Start guide with monitoring options
- Better organization of production features

### Fixed
- Architecture diagrams now render correctly on GitHub (Mermaid format)
- Dark mode visibility for diagrams (high-contrast colors)

## [0.1.0] - 2026-02-03

### Added
- Initial project structure
- Multi-agent system (Specs, Maintenance, Troubleshoot)
- RAG pipeline with pgvector
- JWT authentication
- Redis caching
- FastAPI REST API
- Docker Compose setup
- Basic documentation

### Security
- PII masking in logs
- Rate limiting
- Input validation

---

## Release Notes

### v0.1.0 - Initial Release
First working version with core functionality:
- Multi-agent AI system for automotive customer service
- RAG-powered documentation search
- Service scheduling
- Diagnostic troubleshooting
- Production-ready API

### v0.2.0 - Feature Release
Major feature release with production-ready monitoring, real-time chat, and comprehensive observability:
- WebSocket real-time chat with streaming responses
- 10 production metrics (Prometheus + Grafana)
- 25+ alerting rules with Alertmanager
- A/B testing framework
- ML observability with drift detection
- Comprehensive documentation

### Upcoming in v0.3.0
- Multi-language support (i18n)
- Voice input/output integration
- Plugin system for custom agents
- Knowledge base versioning

---

## Migration Guides

### v0.1.0 → v0.2.0

**New dependencies:**
```bash
pip install -r requirements.txt --upgrade
```

**Environment variables:**
No breaking changes. Metrics are optional and backward-compatible.

**Database migrations:**
No schema changes required.

**Configuration:**
Optional: Add Prometheus and Grafana via `docker-compose.metrics.yml`

---

## Links

- **Repository**: https://github.com/Dumorro/genai-auto
- **Documentation**: [docs/](docs/)
- **Issues**: https://github.com/Dumorro/genai-auto/issues
- **Releases**: https://github.com/Dumorro/genai-auto/releases
