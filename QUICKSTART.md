# 🚀 Quick Start - GenAI Auto

Get up and running in 5 minutes!

---

## Prerequisites

- Docker & Docker Compose installed
- OpenRouter API key (free tier available)

---

## Setup in 4 Steps

### 1️⃣ Get OpenRouter API Key

1. Go to: https://openrouter.ai/keys
2. Sign up (free)
3. Create a new API key
4. Copy the key (starts with `sk-or-v1-...`)

### 2️⃣ Configure Environment

```bash
cd genai-auto

# Edit .env file
nano .env  # or: code .env

# Add your API key:
OPENROUTER_API_KEY=sk-or-v1-YOUR-KEY-HERE
```

**✅ JWT secret is already configured (auto-generated)**

### 3️⃣ Start Services

**Option A: Basic (API only)**
```bash
docker-compose up -d
```

**Option B: Full Stack (with Prometheus + Grafana)**
```bash
docker-compose -f docker-compose.yml -f docker-compose.metrics.yml up -d
```

**Wait for services to be healthy (~30 seconds)**

### 4️⃣ Seed Knowledge Base

```bash
docker-compose exec api python scripts/seed_knowledge_base.py
```

**Expected output:**
```
🚗 GenAI Auto - Knowledge Base Seeder
==================================================
📥 Ingesting documents...
   📄 specs_genautox1_2024.md...
      ✅ 15 chunks, 3250 tokens
...
✨ Seeding complete!
```

---

## ✅ Verify Installation

### Check API Health

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy"}
```

### Access API Docs

```bash
open http://localhost:8000/docs
# Or visit: http://localhost:8000/docs in browser
```

### Test Chat (no auth)

```bash
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the engine power of GenAuto X1?"}'
```

### Create User & Login

**Register:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123",
    "name": "Test User"
  }'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "securepass123"
  }'
```

**Response:**
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Use token:**
```bash
TOKEN="<your-access-token>"

curl -X POST http://localhost:8000/api/v1/chat \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "How often should I change the oil?"}'
```

---

## 📊 Access Monitoring (if enabled)

### Prometheus
```bash
open http://localhost:9090
```

**Example queries:**
- `rate(request_latency_seconds_count[5m])` - Request rate
- `histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m]))` - P95 latency
- `rate(llm_cost_dollars_total[1h]) * 3600` - Cost per hour

### Grafana
```bash
open http://localhost:3000
# Login: admin / admin
```

**Pre-configured dashboard:** GenAI Auto Metrics

### Alertmanager
```bash
open http://localhost:9093
```

---

## 🔧 Useful Commands

### View Logs
```bash
# All services
docker-compose logs -f

# API only
docker-compose logs -f api

# Last 100 lines
docker-compose logs --tail=100 api
```

### Restart Services
```bash
docker-compose restart

# Specific service
docker-compose restart api
```

### Stop Everything
```bash
docker-compose down

# Stop and remove volumes (fresh start)
docker-compose down -v
```

### Rebuild After Code Changes
```bash
docker-compose up -d --build
```

### Execute Commands Inside Container
```bash
# Python shell
docker-compose exec api python

# Run script
docker-compose exec api python scripts/your_script.py

# Shell access
docker-compose exec api bash
```

---

## 🐛 Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or change port in docker-compose.yml:
# ports:
#   - "8001:8000"
```

### Container Won't Start
```bash
# Check logs
docker-compose logs api

# Common issues:
# 1. OPENROUTER_API_KEY not set → Edit .env
# 2. Port conflict → Change port mapping
# 3. Database not ready → Wait 30s, then restart
```

### Database Connection Error
```bash
# Wait for postgres to be fully ready
docker-compose logs postgres | grep "ready to accept"

# Restart API after postgres is ready
docker-compose restart api
```

### "No such file or directory" Error
```bash
# Ensure you're in project root
cd genai-auto

# Verify .env exists
ls -la .env
```

---

## 📚 Next Steps

### 1. Explore API Documentation
- Visit: http://localhost:8000/docs
- Try the interactive endpoints
- Read endpoint descriptions

### 2. Test Different Agents
```bash
# Specs Agent (RAG)
{"message": "What are the dimensions of GenAuto X1?"}

# Maintenance Agent
{"message": "When should I change the oil?"}

# Troubleshoot Agent
{"message": "My check engine light is on, what should I do?"}
```

### 3. Upload Custom Documents
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@your_manual.pdf" \
  -F "document_type=manual"
```

### 4. Monitor Performance
- Track metrics in Grafana
- Set up custom alerts in Prometheus
- Analyze user feedback trends

### 5. Integrate with Your App
- Use REST API endpoints
- Implement authentication flow
- Handle human handoff webhooks

---

## 🎯 Production Checklist

Before deploying to production:

- [ ] Change `JWT_SECRET_KEY` in .env (use `openssl rand -hex 32`)
- [ ] Set strong database password
- [ ] Configure HTTPS/TLS
- [ ] Set up proper backup strategy
- [ ] Configure monitoring alerts
- [ ] Set up log aggregation
- [ ] Enable rate limiting
- [ ] Review CORS settings
- [ ] Set up proper firewall rules
- [ ] Configure human handoff webhook
- [ ] Test disaster recovery

---

## 📖 Full Documentation

- **Architecture:** [docs/architecture/ARCHITECTURE.md](docs/architecture/ARCHITECTURE.md)
- **Metrics Guide:** [docs/METRICS.md](docs/METRICS.md)
- **Bug Fixes:** [BUGFIX_WEBSOCKET_EMPTY_RESPONSE.md](docs/reports/bugfixes/BUGFIX_WEBSOCKET_EMPTY_RESPONSE.md)
- **API Reference:** http://localhost:8000/docs (when running)

---

## 💬 Support

- 📧 Email: tfcoelho@msn.com
- 🐛 Issues: [GitHub Issues](https://github.com/Dumorro/genai-auto/issues)
- 📚 Docs: [README.md](README.md)

---

**Happy coding! 🚗💨**
