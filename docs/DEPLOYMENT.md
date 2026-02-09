# GenAI Auto -- Production Deployment Guide

Complete guide for deploying GenAI Auto (multi-agent AI system for automotive customer service) to production environments using Docker Compose.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Quick Deployment](#2-quick-deployment)
3. [Service Architecture](#3-service-architecture)
4. [Environment Configuration](#4-environment-configuration)
5. [Reverse Proxy Setup (Nginx)](#5-reverse-proxy-setup-nginx)
6. [TLS/HTTPS with Let's Encrypt](#6-tlshttps-with-lets-encrypt)
7. [Health Checks](#7-health-checks)
8. [Backup and Restore](#8-backup-and-restore)
9. [Scaling Strategies](#9-scaling-strategies)
10. [Cost Optimization](#10-cost-optimization)
11. [Monitoring Setup](#11-monitoring-setup)
12. [Troubleshooting](#12-troubleshooting)
13. [Production Security Checklist](#13-production-security-checklist)

---

## 1. Prerequisites

### Required Software

| Software       | Minimum Version | Purpose                        |
|----------------|-----------------|--------------------------------|
| Docker         | 24.0+           | Container runtime              |
| Docker Compose | 2.20+           | Multi-container orchestration  |
| Git            | 2.30+           | Source code management         |

Verify your Docker installation:

```bash
docker --version        # Docker version 24.0+
docker compose version  # Docker Compose version v2.20+
```

### Required Credentials

- **OpenRouter API Key** -- Sign up at [openrouter.ai](https://openrouter.ai/) (free tier available)
- A server or VM with at least **2 CPU cores** and **4 GB RAM** for the base stack
- A domain name (for production TLS)

### System Requirements

| Deployment     | CPU    | RAM    | Disk   |
|----------------|--------|--------|--------|
| Minimum (API)  | 2 core | 4 GB   | 20 GB  |
| Recommended    | 4 core | 8 GB   | 50 GB  |
| Full + Monitor | 4 core | 16 GB  | 100 GB |

---

## 2. Quick Deployment

### 2.1 Clone and Configure

```bash
git clone https://github.com/your-org/genai-auto.git
cd genai-auto

# Create environment file from the template
cp .env.example .env
```

Edit `.env` with production values (see [Section 4](#4-environment-configuration) for details):

```bash
# At minimum, set these:
OPENROUTER_API_KEY=sk-or-v1-your-real-key
POSTGRES_PASSWORD=a-strong-random-password
JWT_SECRET_KEY=$(openssl rand -hex 32)
```

### 2.2 Basic Deployment (API + Database + Cache)

Start the core services (PostgreSQL with pgvector, Redis, and the FastAPI application):

```bash
docker compose up -d
```

This starts three services:
- **postgres** (pgvector/pgvector:pg16) on port 5432
- **redis** (redis:7-alpine) on port 6379
- **api** (custom Dockerfile) on port 8000

Verify everything is running:

```bash
docker compose ps
docker compose logs api --tail=50
```

The API will be available at `http://localhost:8000`. The interactive documentation is at `http://localhost:8000/docs`.

### 2.3 Full Stack Deployment (API + Monitoring + PGAdmin)

Launch the entire stack including Prometheus, Grafana, Alertmanager, and PGAdmin:

```bash
docker compose --profile tools \
  -f docker-compose.yml \
  -f docker-compose.metrics.yml \
  up -d
```

This starts all seven services:

| Service       | URL                          | Purpose                     |
|---------------|------------------------------|-----------------------------|
| API           | http://localhost:8000        | GenAI Auto application      |
| API Docs      | http://localhost:8000/docs   | Swagger/OpenAPI docs        |
| Chat UI       | http://localhost:8000/chat   | Frontend chat interface     |
| Prometheus    | http://localhost:9090        | Metrics collection          |
| Grafana       | http://localhost:3000        | Dashboards (admin/admin)    |
| Alertmanager  | http://localhost:9093        | Alert routing               |
| PGAdmin       | http://localhost:5050        | Database management         |

### 2.4 Verify Deployment

```bash
# Check all containers are healthy
docker compose ps

# Test the health endpoint
curl http://localhost:8000/health

# Test the chat endpoint (requires auth token)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What services do you offer?"}'

# Verify Prometheus is scraping metrics
curl http://localhost:9090/api/v1/targets
```

---

## 3. Service Architecture

```
                         +------------------+
                         |   Nginx Reverse  |
                         |   Proxy (:443)   |
                         +--------+---------+
                                  |
                    +-------------+-------------+
                    |             |              |
              HTTP (:8000)  WS (:8000)   Static files
                    |             |
           +--------+-------------+---------+
           |        GenAI Auto API          |
           |   (uvicorn + FastAPI)          |
           |   Container: genai-auto-api    |
           +--+----------+----------+------++
              |          |          |       |
              v          v          v       v
    +---------+--+ +-----+----+ +--+-------++ +--------+
    | PostgreSQL | |  Redis   | | OpenRouter | | Webhook|
    | + pgvector | |  Cache   | |  LLM API   | | (opt.) |
    | :5432      | |  :6379   | |  External  | |        |
    +-----+------+ +----+-----+ +-----------+ +--------+
          |              |
    +-----+------+ +----+-----+
    | postgres_  | | redis_   |
    | data vol   | | data vol |
    +------------+ +----------+

    +-----------+    +----------+    +--------------+
    | Prometheus| -> | Grafana  |    | Alertmanager |
    |   :9090   |    |  :3000   |    |    :9093     |
    +-----------+    +----------+    +--------------+
         |                                |
    (scrapes /api/v1/metrics)      (Slack/Email/PD)
```

### Container Details

| Container           | Image                      | Restart Policy  | Depends On                |
|---------------------|----------------------------|-----------------|---------------------------|
| genai-auto-db       | pgvector/pgvector:pg16     | (default)       | --                        |
| genai-auto-redis    | redis:7-alpine             | (default)       | --                        |
| genai-auto-api      | Custom (Dockerfile)        | unless-stopped  | postgres, redis (healthy) |
| genai-auto-pgadmin  | dpage/pgadmin4:latest      | (default)       | postgres (profile: tools) |
| genai-prometheus    | prom/prometheus:latest      | unless-stopped  | --                        |
| genai-grafana       | grafana/grafana:latest      | unless-stopped  | prometheus                |
| genai-alertmanager  | prom/alertmanager:latest    | unless-stopped  | --                        |

### Network

All services run on a shared Docker network named `genai-auto-network`. Internal DNS resolution is automatic -- services reference each other by container service name (e.g., `postgres`, `redis`, `api`).

### Database Schema

The PostgreSQL database is initialized automatically via `scripts/init_postgres.sql`, which creates:

- **pgvector** extension for vector similarity search
- **users** -- JWT authentication accounts
- **customers** -- Customer profiles
- **vehicles** -- Vehicle records linked to customers
- **service_history** -- Service records linked to vehicles
- **appointments** -- Scheduled service appointments
- **document_embeddings** -- RAG document store with 768-dimensional vectors (nomic-embed-text-v1.5)
- **conversations** -- Chat session history with JSONB messages

---

## 4. Environment Configuration

### 4.1 Production .env File

Create a `.env` file in the project root. Every variable below is read by the `api` service in `docker-compose.yml`.

```bash
# =============================================================================
# DATABASE
# =============================================================================
POSTGRES_USER=genai
POSTGRES_PASSWORD=<STRONG_RANDOM_PASSWORD>   # openssl rand -base64 24
POSTGRES_DB=genai_auto

# =============================================================================
# LLM PROVIDER (OpenRouter)
# =============================================================================
OPENROUTER_API_KEY=sk-or-v1-<your-production-key>
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1

# Model selection -- see Section 10 for cost breakdown
LLM_MODEL=tngtech/deepseek-r1t2-chimera:free
EMBEDDING_MODEL=nomic-ai/nomic-embed-text-v1.5

# =============================================================================
# SECURITY -- JWT Authentication
# =============================================================================
# CRITICAL: Generate a unique secret for production
JWT_SECRET_KEY=<RUN: openssl rand -hex 32>
JWT_ACCESS_EXPIRE_MINUTES=30
JWT_REFRESH_EXPIRE_DAYS=7

# =============================================================================
# PERFORMANCE -- Redis Caching
# =============================================================================
# Internal Docker URL (do not change unless customizing network)
REDIS_URL=redis://redis:6379
CACHE_ENABLED=true
CACHE_TTL=3600

# =============================================================================
# AI BEHAVIOR
# =============================================================================
CONFIDENCE_THRESHOLD=0.7
HUMAN_SUPPORT_WEBHOOK=https://your-ticketing-system.com/api/webhook

# =============================================================================
# PRIVACY
# =============================================================================
MASK_PII=true

# =============================================================================
# OBSERVABILITY
# =============================================================================
LANGCHAIN_TRACING_V2=false
LANGCHAIN_API_KEY=
LOG_LEVEL=WARNING       # Use WARNING or ERROR in production

# =============================================================================
# OPTIONAL TOOLS
# =============================================================================
PGADMIN_EMAIL=admin@yourcompany.com
PGADMIN_PASSWORD=<STRONG_PASSWORD>

# Scheduler integration (external)
SCHEDULER_API_URL=http://localhost:9000
SCHEDULER_API_KEY=
```

### 4.2 Critical Production Settings

These settings MUST be changed from their defaults before going live:

| Variable            | Default (dev)                              | Production Requirement                       |
|---------------------|--------------------------------------------|----------------------------------------------|
| `POSTGRES_PASSWORD` | `genai_secret`                             | Strong random password (24+ characters)      |
| `JWT_SECRET_KEY`    | `change-me-in-production`                  | `openssl rand -hex 32`                       |
| `LOG_LEVEL`         | `INFO`                                     | `WARNING` or `ERROR`                         |
| `MASK_PII`          | `true`                                     | Must remain `true`                           |
| `PGADMIN_PASSWORD`  | `admin`                                    | Strong password or disable PGAdmin entirely  |

### 4.3 Docker Compose Production Overrides

For production, create a `docker-compose.prod.yml` override that tightens security:

```yaml
version: '3.8'

services:
  postgres:
    ports: []   # Do not expose database to host

  redis:
    ports: []   # Do not expose Redis to host
    command: redis-server --requirepass ${REDIS_PASSWORD}

  api:
    volumes:
      # Remove source code mount in production (use built image)
      - ./data:/app/data
    environment:
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G

  pgadmin:
    profiles:
      - disabled   # Disable PGAdmin in production
```

Deploy with the production override:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 5. Reverse Proxy Setup (Nginx)

### 5.1 Why Use a Reverse Proxy

- TLS termination (HTTPS)
- WebSocket proxying for the real-time chat interface
- Rate limiting
- Static file caching
- Single entry point on ports 80/443

### 5.2 Nginx Configuration

Create `/etc/nginx/sites-available/genai-auto`:

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req_zone $binary_remote_addr zone=auth_limit:10m rate=5r/s;

# Upstream for GenAI Auto API
upstream genai_api {
    server 127.0.0.1:8000;
    keepalive 32;
}

# Redirect HTTP to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name genai.yourdomain.com;
    return 301 https://$host$request_uri;
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name genai.yourdomain.com;

    # TLS certificates (managed by Certbot -- see Section 6)
    ssl_certificate /etc/letsencrypt/live/genai.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/genai.yourdomain.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;

    # Logging
    access_log /var/log/nginx/genai-auto-access.log;
    error_log /var/log/nginx/genai-auto-error.log;

    # Request size limit (for document uploads)
    client_max_body_size 50M;

    # ---------------------------------------------------------------
    # WebSocket endpoint -- GenAI Auto chat uses /ws/{session_id}
    # ---------------------------------------------------------------
    location /ws/ {
        proxy_pass http://genai_api;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # WebSocket timeout (keep alive for long chat sessions)
        proxy_read_timeout 3600s;
        proxy_send_timeout 3600s;
    }

    # ---------------------------------------------------------------
    # Auth endpoints -- stricter rate limiting
    # ---------------------------------------------------------------
    location /api/v1/auth/ {
        limit_req zone=auth_limit burst=10 nodelay;

        proxy_pass http://genai_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ---------------------------------------------------------------
    # API endpoints
    # ---------------------------------------------------------------
    location /api/ {
        limit_req zone=api_limit burst=50 nodelay;

        proxy_pass http://genai_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
    }

    # ---------------------------------------------------------------
    # Health check (no rate limit)
    # ---------------------------------------------------------------
    location /health {
        proxy_pass http://genai_api;
        proxy_set_header Host $host;
    }

    # ---------------------------------------------------------------
    # Frontend / Chat UI
    # ---------------------------------------------------------------
    location / {
        proxy_pass http://genai_api;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # ---------------------------------------------------------------
    # Block access to monitoring from the public internet
    # ---------------------------------------------------------------
    location /api/v1/metrics {
        allow 10.0.0.0/8;
        allow 172.16.0.0/12;
        allow 192.168.0.0/16;
        allow 127.0.0.1;
        deny all;

        proxy_pass http://genai_api;
        proxy_set_header Host $host;
    }
}
```

### 5.3 Enable and Test

```bash
# Create symlink to enable the site
sudo ln -s /etc/nginx/sites-available/genai-auto /etc/nginx/sites-enabled/

# Test configuration syntax
sudo nginx -t

# Reload Nginx
sudo systemctl reload nginx
```

---

## 6. TLS/HTTPS with Let's Encrypt

### 6.1 Install Certbot

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install certbot python3-certbot-nginx

# Amazon Linux / RHEL
sudo yum install certbot python3-certbot-nginx
```

### 6.2 Obtain Certificate

```bash
sudo certbot --nginx -d genai.yourdomain.com
```

Certbot will automatically:
1. Verify domain ownership via HTTP challenge
2. Obtain the certificate
3. Modify the Nginx configuration to use TLS
4. Set up auto-renewal

### 6.3 Verify Auto-Renewal

```bash
# Test the renewal process (dry run)
sudo certbot renew --dry-run

# Verify the systemd timer is active
sudo systemctl status certbot.timer
```

Certificates renew automatically every 60-90 days. If you need to force a renewal:

```bash
sudo certbot renew --force-renewal
sudo systemctl reload nginx
```

---

## 7. Health Checks

### 7.1 Built-In Container Health Checks

The `docker-compose.yml` defines health checks for the data services:

**PostgreSQL:**
```yaml
healthcheck:
  test: ["CMD-SHELL", "pg_isready -U genai -d genai_auto"]
  interval: 10s
  timeout: 5s
  retries: 5
```

**Redis:**
```yaml
healthcheck:
  test: ["CMD", "redis-cli", "ping"]
  interval: 10s
  timeout: 5s
  retries: 5
```

The `api` service uses `depends_on` with `condition: service_healthy` so it will not start until both PostgreSQL and Redis are verified healthy.

### 7.2 Application Health Endpoint

The API exposes a `/health` endpoint:

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "redis": "connected",
    "llm": "configured"
  }
}
```

### 7.3 External Health Monitoring

Set up an external uptime monitor (e.g., UptimeRobot, Pingdom, or a cron job) to poll the health endpoint:

```bash
# Simple cron-based health check (add to crontab -e)
*/5 * * * * curl -sf http://localhost:8000/health > /dev/null || \
  echo "GenAI Auto API is DOWN at $(date)" | mail -s "ALERT: API Down" ops@yourcompany.com
```

### 7.4 Docker Health Status

```bash
# Check health status for all containers
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"

# Check a specific container
docker inspect --format='{{.State.Health.Status}}' genai-auto-db
```

---

## 8. Backup and Restore

### 8.1 PostgreSQL Backup

#### Full Database Dump

```bash
# Backup to compressed SQL file
docker exec genai-auto-db pg_dump \
  -U genai \
  -d genai_auto \
  --format=custom \
  --compress=9 \
  > backup_$(date +%Y%m%d_%H%M%S).dump

# Backup as plain SQL (human-readable)
docker exec genai-auto-db pg_dump \
  -U genai \
  -d genai_auto \
  > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### Backup Specific Tables

```bash
# Backup only conversation data
docker exec genai-auto-db pg_dump \
  -U genai \
  -d genai_auto \
  -t conversations \
  -t document_embeddings \
  --format=custom \
  > backup_rag_data_$(date +%Y%m%d).dump
```

#### Automated Daily Backups

Create `/opt/genai-auto/backup.sh`:

```bash
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/opt/genai-auto/backups"
RETENTION_DAYS=30
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

# Run the backup
docker exec genai-auto-db pg_dump \
  -U genai \
  -d genai_auto \
  --format=custom \
  --compress=9 \
  > "${BACKUP_DIR}/genai_auto_${TIMESTAMP}.dump"

# Remove backups older than retention period
find "$BACKUP_DIR" -name "*.dump" -mtime +${RETENTION_DAYS} -delete

echo "[$(date)] Backup completed: genai_auto_${TIMESTAMP}.dump"
```

Add to crontab:

```bash
chmod +x /opt/genai-auto/backup.sh

# Run daily at 2:00 AM
echo "0 2 * * * /opt/genai-auto/backup.sh >> /var/log/genai-backup.log 2>&1" | crontab -
```

### 8.2 Restore from Backup

```bash
# Stop the API to prevent writes during restore
docker compose stop api

# Restore from custom-format dump
docker exec -i genai-auto-db pg_restore \
  -U genai \
  -d genai_auto \
  --clean \
  --if-exists \
  < backup_20260101_020000.dump

# Restart the API
docker compose start api
```

### 8.3 Redis Data

Redis data is persisted to the `redis_data` volume. For backup:

```bash
# Trigger a synchronous save
docker exec genai-auto-redis redis-cli BGSAVE

# Copy the dump file
docker cp genai-auto-redis:/data/dump.rdb ./redis_backup_$(date +%Y%m%d).rdb
```

### 8.4 Volume Backup (Full)

For a complete backup of all Docker volumes:

```bash
# Backup PostgreSQL volume
docker run --rm \
  -v genai-auto_postgres_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/postgres_volume_$(date +%Y%m%d).tar.gz -C /data .

# Backup Redis volume
docker run --rm \
  -v genai-auto_redis_data:/data \
  -v $(pwd)/backups:/backup \
  alpine tar czf /backup/redis_volume_$(date +%Y%m%d).tar.gz -C /data .
```

---

## 9. Scaling Strategies

### 9.1 Vertical Scaling

Increase resources allocated to individual containers via `docker-compose.prod.yml`:

```yaml
services:
  api:
    deploy:
      resources:
        limits:
          cpus: '4.0'
          memory: 8G
        reservations:
          cpus: '1.0'
          memory: 2G

  postgres:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
    command: >
      postgres
        -c shared_buffers=1GB
        -c effective_cache_size=3GB
        -c work_mem=64MB
        -c maintenance_work_mem=256MB
        -c max_connections=200
```

### 9.2 Horizontal Scaling (Multiple API Instances)

Scale the API service behind the Nginx load balancer:

```bash
# Scale API to 3 instances
docker compose up -d --scale api=3
```

Update the Nginx upstream block to load-balance:

```nginx
upstream genai_api {
    least_conn;
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
    keepalive 32;
}
```

When scaling horizontally, assign unique ports by creating a `docker-compose.scale.yml`:

```yaml
version: '3.8'
services:
  api:
    ports: []   # Remove the fixed port mapping
    deploy:
      replicas: 3
```

**Important considerations for horizontal scaling:**
- Redis is already shared -- all API instances use the same cache
- PostgreSQL is already shared -- connection pooling is handled by SQLAlchemy
- WebSocket sessions are stateful -- use sticky sessions (ip_hash) or an external session store
- The `/data` volume must be shared across instances (use NFS or a shared filesystem)

### 9.3 Database Scaling

For high-traffic deployments, consider:

```bash
# Add read replicas (PostgreSQL streaming replication)
# Increase the IVFFlat index lists for better vector search performance:
# In init_postgres.sql, adjust:
#   WITH (lists = 100)  -->  WITH (lists = 500)  for 100k+ documents
```

### 9.4 Scaling Reference Table

| Traffic Level       | API Replicas | PostgreSQL      | Redis    | Estimated Cost/mo |
|---------------------|--------------|-----------------|----------|--------------------|
| Low (< 100 req/min) | 1           | 2 CPU / 4 GB    | 1 GB     | $20-40             |
| Medium (< 1k/min)   | 2-3         | 4 CPU / 8 GB    | 2 GB     | $80-150            |
| High (< 10k/min)    | 4-8         | 8 CPU / 16 GB   | 4 GB     | $300-600           |

---

## 10. Cost Optimization

### 10.1 Free LLM Models (via OpenRouter)

GenAI Auto is designed to work with OpenRouter's free tier. These models have no per-token cost:

| Model                                      | Type       | Quality   | Speed     |
|--------------------------------------------|------------|-----------|-----------|
| `tngtech/deepseek-r1t2-chimera:free`       | Reasoning  | High      | Moderate  |
| `meta-llama/llama-3.1-8b-instruct:free`    | Chat       | Good      | Fast      |
| `google/gemma-2-9b-it:free`                | Chat       | Good      | Fast      |
| `mistralai/mistral-7b-instruct:free`       | Chat       | Good      | Fast      |
| `qwen/qwen-2-7b-instruct:free`            | Chat       | Good      | Fast      |

Set the model in your `.env`:

```bash
LLM_MODEL=tngtech/deepseek-r1t2-chimera:free
```

### 10.2 Paid Models (Higher Quality)

For production workloads that require higher quality:

| Model                            | Cost (per 1M tokens)     | Best For                |
|----------------------------------|--------------------------|-------------------------|
| `openai/gpt-4o-mini`            | ~$0.15 input / $0.60 out | Cost-effective quality  |
| `anthropic/claude-3.5-sonnet`   | ~$3.00 input / $15.00 out| Complex reasoning       |
| `openai/gpt-4o`                 | ~$2.50 input / $10.00 out| General production      |

### 10.3 Cost Reduction Strategies

1. **Enable Redis caching** -- `CACHE_ENABLED=true` prevents repeated LLM calls for similar queries. A 40%+ cache hit rate can cut LLM costs nearly in half.

2. **Use free embedding model** -- `nomic-ai/nomic-embed-text-v1.5` via OpenRouter has no cost for embeddings.

3. **Set a confidence threshold** -- `CONFIDENCE_THRESHOLD=0.7` hands off uncertain queries to humans rather than generating expensive follow-up LLM calls.

4. **Monitor with alerts** -- The built-in Prometheus alerts trigger at:
   - Warning: LLM spend > $10/hour
   - Critical: LLM spend > $50/hour

5. **Start free, upgrade selectively** -- Use free models in development and staging. Only use paid models in production when quality requirements demand it.

### 10.4 Estimated Monthly Costs

| Component         | Free Tier             | Production (Paid LLM)  |
|-------------------|-----------------------|------------------------|
| LLM API           | $0                    | $50-500                |
| Embedding API     | $0                    | $0                     |
| Infrastructure    | $20 (VPS)             | $80-200 (VPS)         |
| **Total**         | **~$20/mo**           | **$130-700/mo**        |

---

## 11. Monitoring Setup

### 11.1 Start the Monitoring Stack

```bash
docker compose -f docker-compose.yml -f docker-compose.metrics.yml up -d
```

### 11.2 Prometheus

**URL:** http://localhost:9090

Prometheus is pre-configured to scrape the GenAI Auto API at `/api/v1/metrics` every 15 seconds. Key configuration from `prometheus.yml`:

- Scrape interval: 15s
- TSDB retention: 15 days
- Alert rules loaded from `alerts.yml`
- Alertmanager target: `alertmanager:9093`

Verify the scrape target is healthy:

```
http://localhost:9090/targets
```

The target `genai-auto-api` should show status `UP`.

### 11.3 Grafana

**URL:** http://localhost:3000
**Login:** admin / admin (change immediately in production)

Grafana is pre-provisioned with:
- **Datasource:** Prometheus (auto-configured via `grafana/datasources/prometheus.yml`)
- **Dashboard:** GenAI Auto Metrics (auto-loaded from `grafana/dashboards/genai-auto-metrics.json`)

To change the default admin password:

```bash
docker exec -it genai-grafana grafana-cli admin reset-admin-password <new-password>
```

### 11.4 Alert Rules

The system ships with 25+ pre-configured alert rules in `alerts.yml`, organized into these groups:

| Group                    | Alerts                                                              |
|--------------------------|---------------------------------------------------------------------|
| **genai_auto_alerts**    | HighLLMCost, CriticalLLMCost, HighLatency, VeryHighLatency, SlowLLMResponse, HighErrorRate, CriticalErrorRate, FrequentLLMErrors, LowUserSatisfaction, VeryLowUserSatisfaction, TooManyInProgressRequests, APIDown, NoMetricsScraped |
| **rag_quality_alerts**   | LowRAGSimilarity, SlowRAGSearch                                    |
| **cache_alerts**         | LowCacheHitRate, HighCacheLatency                                  |
| **handoff_alerts**       | HighHandoffRate, FrequentLowConfidenceHandoffs                     |
| **task_completion_alerts**| LowTaskCompletionRate, HighAbandonmentRate                        |
| **routing_alerts**       | LowRoutingConfidence, HighReroutingRate                            |

### 11.5 Alertmanager

**URL:** http://localhost:9093

Alertmanager routes alerts to different channels based on severity:

| Severity / Type    | Slack Channel         | Email | PagerDuty |
|--------------------|-----------------------|-------|-----------|
| Critical           | #genai-critical       | Yes   | Yes       |
| Warning            | #genai-alerts         | No    | No        |
| Cost alerts        | #genai-cost-alerts    | No    | No        |
| Performance alerts | #genai-performance    | No    | No        |

Configure your notification channels in `alertmanager.yml`:

```yaml
global:
  slack_api_url: 'https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK'
```

**Inhibition rules** are pre-configured:
- If `APIDown` fires, all other alerts are suppressed (since they would be side effects)
- If `CriticalLLMCost` fires, the `HighLLMCost` warning is suppressed (avoid duplicate noise)

### 11.6 Key Metrics to Watch

| Metric                                | What It Tells You                    | Alert Threshold        |
|---------------------------------------|--------------------------------------|------------------------|
| `llm_cost_dollars_total`              | Cumulative LLM spend                 | > $10/hr warn, $50 crit|
| `request_latency_seconds` (P95)       | API response time                    | > 5s warn, > 10s crit  |
| `http_errors_total / requests`        | Error rate                           | > 5% warn, > 20% crit  |
| `cache_operations_total{op="hit"}`    | Cache hit rate                       | < 40% warn             |
| `rag_similarity_score` (avg)          | RAG retrieval quality                | < 0.6 warn             |
| `human_handoff_total`                 | Handoff rate to humans               | > 20% warn             |
| `agent_routing_confidence` (avg)      | Agent selection accuracy             | < 0.65 warn            |

---

## 12. Troubleshooting

### 12.1 API Container Will Not Start

**Symptom:** `genai-auto-api` exits immediately or keeps restarting.

```bash
# Check the logs
docker compose logs api --tail=100

# Common causes:
# 1. Database not ready -- api depends on postgres health check, but check manually:
docker compose logs postgres --tail=50

# 2. Missing environment variable
docker compose config   # Verify resolved config

# 3. Port already in use
lsof -i :8000
```

**Fix:** Ensure PostgreSQL and Redis are healthy before the API starts:

```bash
docker compose up -d postgres redis
docker compose ps    # Wait for "healthy" status
docker compose up -d api
```

### 12.2 Database Connection Refused

**Symptom:** `connection refused` or `could not connect to server` in API logs.

```bash
# Verify PostgreSQL is running and healthy
docker exec genai-auto-db pg_isready -U genai -d genai_auto

# Check if the init script ran successfully
docker compose logs postgres | grep -i error

# Verify the DATABASE_URL resolves correctly inside the API container
docker exec genai-auto-api env | grep DATABASE_URL
```

**Fix:** If the database was never initialized, remove the volume and restart:

```bash
docker compose down
docker volume rm genai-auto_postgres_data
docker compose up -d
```

### 12.3 WebSocket Connection Fails

**Symptom:** Chat UI shows "Connection lost" or WebSocket handshake fails.

```bash
# Test WebSocket directly (requires wscat: npm install -g wscat)
wscat -c ws://localhost:8000/ws/test-session

# If behind Nginx, check the proxy configuration includes:
#   proxy_http_version 1.1;
#   proxy_set_header Upgrade $http_upgrade;
#   proxy_set_header Connection "upgrade";
```

**Common causes:**
1. Nginx not configured for WebSocket upgrade (see Section 5.2)
2. Proxy timeout too short -- set `proxy_read_timeout 3600s` for long chat sessions
3. Load balancer stripping Upgrade headers -- ensure the load balancer supports WebSocket

### 12.4 LLM Returns Empty Responses

**Symptom:** Chat returns empty or null responses.

```bash
# Check the API key is set
docker exec genai-auto-api env | grep OPENROUTER_API_KEY

# Test the OpenRouter API directly
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check if the model is still available
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" | \
  python3 -c "import sys,json; models=[m['id'] for m in json.load(sys.stdin)['data']]; print('tngtech/deepseek-r1t2-chimera:free' in models)"
```

**Fix:** Free models occasionally have downtime. Switch to a different free model:

```bash
# In .env, change:
LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free

# Restart the API
docker compose restart api
```

### 12.5 Redis Cache Issues

**Symptom:** Slow responses despite caching being enabled, or stale data.

```bash
# Verify Redis is reachable from the API container
docker exec genai-auto-api python3 -c "import redis; r=redis.from_url('redis://redis:6379'); print(r.ping())"

# Check cache statistics
docker exec genai-auto-redis redis-cli INFO stats | grep keyspace

# Flush the cache if stale data is suspected
docker exec genai-auto-redis redis-cli FLUSHALL
```

### 12.6 Out of Disk Space

**Symptom:** Containers crash or cannot write to volumes.

```bash
# Check disk usage
df -h

# Check Docker disk usage
docker system df

# Clean up unused images, containers, and volumes
docker system prune -a --volumes
```

### 12.7 Prometheus Not Scraping Metrics

**Symptom:** Grafana dashboards show "No data".

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# Verify the metrics endpoint is accessible from the Prometheus container
docker exec genai-prometheus wget -qO- http://api:8000/api/v1/metrics

# Check Prometheus logs
docker compose -f docker-compose.yml -f docker-compose.metrics.yml logs prometheus --tail=50
```

### 12.8 Container Resource Limits

```bash
# View real-time resource usage for all containers
docker stats --no-stream

# Check if any container was OOM-killed
docker inspect genai-auto-api | grep -A5 "State"
```

---

## 13. Production Security Checklist

Use this checklist before going live. Every item marked with **[CRITICAL]** must be addressed.

### Authentication and Secrets

- [ ] **[CRITICAL]** Generate a unique JWT secret: `openssl rand -hex 32`
- [ ] **[CRITICAL]** Change the default PostgreSQL password from `genai_secret`
- [ ] **[CRITICAL]** Change the default PGAdmin password from `admin` (or disable PGAdmin)
- [ ] **[CRITICAL]** Never commit `.env` to version control (verify `.gitignore`)
- [ ] Set `JWT_ACCESS_EXPIRE_MINUTES` to 15-30 for production
- [ ] Set `JWT_REFRESH_EXPIRE_DAYS` to 7 or less
- [ ] Rotate the `OPENROUTER_API_KEY` periodically

### Network Security

- [ ] **[CRITICAL]** Do not expose PostgreSQL port (5432) to the public internet
- [ ] **[CRITICAL]** Do not expose Redis port (6379) to the public internet
- [ ] **[CRITICAL]** Enable TLS/HTTPS via Nginx + Let's Encrypt (Section 6)
- [ ] Block public access to `/api/v1/metrics` (internal only)
- [ ] Block public access to Prometheus (9090), Grafana (3000), Alertmanager (9093)
- [ ] Configure Redis to require a password (`--requirepass`)
- [ ] Restrict CORS origins (replace `allow_origins=["*"]` with specific domains)
- [ ] Enable Nginx rate limiting (Section 5.2)

### Data Protection

- [ ] **[CRITICAL]** Keep `MASK_PII=true` in production
- [ ] Enable automated database backups (Section 8)
- [ ] Test backup restoration procedure at least once before going live
- [ ] Encrypt backups at rest if stored off-server

### Logging and Monitoring

- [ ] Set `LOG_LEVEL=WARNING` or `ERROR` in production (avoid logging sensitive data)
- [ ] Configure Alertmanager with real notification channels (Slack, email, PagerDuty)
- [ ] Set up external uptime monitoring
- [ ] Change the Grafana admin password from the default `admin`

### Container Security

- [ ] Use specific image tags instead of `latest` in production compose files
- [ ] Set resource limits on all containers (`deploy.resources.limits`)
- [ ] Run containers as non-root users where possible
- [ ] Keep Docker and all images updated with security patches
- [ ] Scan container images for vulnerabilities (`docker scout cves`)

### Infrastructure

- [ ] Configure firewall rules (only allow ports 80, 443 from the internet)
- [ ] Enable automatic security updates on the host OS
- [ ] Set up log rotation for Docker logs and Nginx logs
- [ ] Document the deployment procedure and maintain a runbook

---

## Quick Reference

### Common Commands

```bash
# Start core services
docker compose up -d

# Start with monitoring
docker compose -f docker-compose.yml -f docker-compose.metrics.yml up -d

# Start with PGAdmin (development tool)
docker compose --profile tools up -d

# View logs
docker compose logs -f api
docker compose logs -f postgres redis

# Restart a single service
docker compose restart api

# Stop everything
docker compose -f docker-compose.yml -f docker-compose.metrics.yml down

# Stop and remove volumes (DESTROYS DATA)
docker compose down -v

# Rebuild the API image after code changes
docker compose build api && docker compose up -d api

# Database shell
docker exec -it genai-auto-db psql -U genai -d genai_auto

# Redis shell
docker exec -it genai-auto-redis redis-cli
```

### Port Reference

| Port  | Service        | Public Access? |
|-------|----------------|----------------|
| 80    | Nginx HTTP     | Yes            |
| 443   | Nginx HTTPS    | Yes            |
| 8000  | FastAPI        | Via Nginx only |
| 5432  | PostgreSQL     | No             |
| 6379  | Redis          | No             |
| 5050  | PGAdmin        | No             |
| 9090  | Prometheus     | No             |
| 3000  | Grafana        | No (or VPN)    |
| 9093  | Alertmanager   | No             |
