# Changelog

All notable changes to GenAI Auto will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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

### Upcoming in v0.2.0
- WebSocket streaming
- Multi-language support
- Voice integration
- Advanced analytics

---

## Migration Guides

### v0.1.0 → v0.2.0 (upcoming)

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
