# GenAI Auto - Metrics Guide

## Overview

GenAI Auto implements **5 essential metrics** for monitoring LLM performance, costs, and user satisfaction:

1. ✅ **Token Usage** (input/output)
2. ✅ **Cost per Request**
3. ✅ **Response Latency** (P95)
4. ✅ **Error Rate**
5. ✅ **User Feedback** (thumbs up/down)

All metrics are exposed in Prometheus format at `/api/v1/metrics`.

---

## Available Metrics

### 1. Token Usage

**Metrics:**
```
llm_tokens_total{type="input", model="...", agent="..."}
llm_tokens_total{type="output", model="...", agent="..."}
```

**Description:** Total tokens consumed by LLM calls, split by input/output.

**Use cases:**
- Track token consumption trends
- Identify verbose agents/models
- Budget forecasting

**Query examples:**
```promql
# Total tokens per hour
rate(llm_tokens_total[1h]) * 3600

# Tokens by agent
sum by (agent) (llm_tokens_total)

# Input vs output ratio
llm_tokens_total{type="output"} / llm_tokens_total{type="input"}
```

---

### 2. Cost per Request

**Metrics:**
```
llm_cost_dollars_total{model="...", agent="..."}
request_cost_dollars (histogram)
```

**Description:** LLM cost tracking in dollars.

**Use cases:**
- Budget monitoring
- Cost attribution by agent
- Alert on high spend

**Query examples:**
```promql
# Cost per hour
rate(llm_cost_dollars_total[1h]) * 3600

# P95 cost per request
histogram_quantile(0.95, request_cost_dollars)

# Most expensive agent
topk(3, sum by (agent) (llm_cost_dollars_total))
```

**Alert example:**
```yaml
- alert: HighLLMCost
  expr: rate(llm_cost_dollars_total[1h]) > 10
  annotations:
    summary: "LLM spend exceeds $10/hour"
```

---

### 3. Response Latency (P95)

**Metrics:**
```
request_latency_seconds{endpoint="...", method="..."}
llm_latency_seconds{model="...", agent="..."}
```

**Description:** Request and LLM call latency distribution.

**Use cases:**
- SLA monitoring (e.g., P95 < 2s)
- Performance regression detection
- Identify slow agents/models

**Query examples:**
```promql
# P95 latency for /chat endpoint
histogram_quantile(0.95, rate(request_latency_seconds_bucket{endpoint="/api/v1/chat"}[5m]))

# P99 LLM latency
histogram_quantile(0.99, rate(llm_latency_seconds_bucket[5m]))

# Slowest agent
topk(1, histogram_quantile(0.95, sum by (agent) (rate(llm_latency_seconds_bucket[5m]))))
```

**Alert example:**
```yaml
- alert: HighLatency
  expr: histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m])) > 5
  annotations:
    summary: "P95 latency exceeds 5 seconds"
```

---

### 4. Error Rate

**Metrics:**
```
http_errors_total{endpoint="...", method="...", status_code="..."}
llm_errors_total{error_type="...", model="..."}
```

**Description:** HTTP and LLM error tracking.

**Error types:**
- `timeout` - LLM request timeout
- `rate_limit` - API rate limit hit
- `api_error` - General API errors
- `validation_error` - Input validation failures

**Use cases:**
- Error rate monitoring
- Incident detection
- Root cause analysis

**Query examples:**
```promql
# Error rate (errors per second)
rate(http_errors_total[5m])

# Error rate percentage
rate(http_errors_total[5m]) / rate(request_latency_seconds_count[5m]) * 100

# Errors by type
sum by (error_type) (llm_errors_total)
```

**Alert example:**
```yaml
- alert: HighErrorRate
  expr: rate(http_errors_total[5m]) / rate(request_latency_seconds_count[5m]) > 0.05
  annotations:
    summary: "Error rate exceeds 5%"
```

---

### 5. User Feedback

**Metrics:**
```
user_feedback_total{sentiment="positive|negative", message_id="..."}
```

**Description:** Thumbs up/down feedback from users.

**Use cases:**
- User satisfaction tracking
- Model/agent quality assessment
- A/B testing

**Query examples:**
```promql
# Positive feedback rate
rate(user_feedback_total{sentiment="positive"}[1h]) / rate(user_feedback_total[1h])

# Feedback by agent (requires joining with message metadata)
sum by (agent) (user_feedback_total)

# Total feedback count
sum(user_feedback_total)
```

---

## Endpoints

### GET /api/v1/metrics

Prometheus metrics endpoint for scraping.

**Response:** Prometheus-formatted metrics

**Example:**
```bash
curl http://localhost:8000/api/v1/metrics

# Output:
# llm_tokens_total{type="input",model="llama-3.1-8b",agent="specs"} 12500.0
# llm_tokens_total{type="output",model="llama-3.1-8b",agent="specs"} 8200.0
# llm_cost_dollars_total{model="llama-3.1-8b",agent="specs"} 0.0
# ...
```

---

### POST /api/v1/feedback

Submit user feedback (thumbs up/down).

**Request:**
```json
{
  "message_id": "msg_123",
  "sentiment": "positive",
  "comment": "Very helpful!"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Feedback recorded",
  "message_id": "msg_123",
  "sentiment": "positive"
}
```

**Example:**
```bash
curl -X POST http://localhost:8000/api/v1/feedback \
  -H "Content-Type: application/json" \
  -d '{
    "message_id": "msg_123",
    "sentiment": "positive",
    "comment": "Great answer!"
  }'
```

---

## Integration Guide

### 1. Add to your chat endpoint

```python
from api.metrics import track_llm_call, track_llm_error, track_endpoint_metrics

@router.post("/chat")
@track_endpoint_metrics('chat')  # Automatic latency tracking
async def chat(request: ChatRequest):
    try:
        start_time = time.time()
        
        # Your LLM call here
        result = await llm.generate(request.message)
        
        duration = time.time() - start_time
        
        # Track metrics
        track_llm_call(
            model="meta-llama/llama-3.1-8b-instruct:free",
            agent="specs",
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            duration=duration
        )
        
        return result
    
    except TimeoutError:
        track_llm_error(error_type='timeout', model='llama-3.1-8b')
        raise
```

### 2. Enable metrics middleware

```python
# In main.py
from api.metrics import metrics_middleware

app = FastAPI()
app.middleware("http")(metrics_middleware)
```

### 3. Register metrics routes

```python
# In main.py
from api.routes.metrics_routes import router as metrics_router

app.include_router(metrics_router)
```

---

## Prometheus Setup

### 1. Install Prometheus

**Docker:**
```yaml
# Add to docker-compose.yml
prometheus:
  image: prom/prometheus:latest
  ports:
    - "9090:9090"
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  command:
    - '--config.file=/etc/prometheus/prometheus.yml'
```

**Config (prometheus.yml):**
```yaml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'genai-auto'
    static_configs:
      - targets: ['api:8000']
    metrics_path: '/api/v1/metrics'
```

### 2. Start Prometheus

```bash
docker-compose up -d prometheus
```

Access: http://localhost:9090

---

## Grafana Dashboard

### 1. Install Grafana

```yaml
# Add to docker-compose.yml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    - GF_SECURITY_ADMIN_PASSWORD=admin
  volumes:
    - grafana-data:/var/lib/grafana
```

### 2. Add Prometheus as data source

1. Go to http://localhost:3000
2. Login (admin/admin)
3. Configuration → Data Sources → Add data source
4. Select Prometheus
5. URL: `http://prometheus:9090`
6. Save & Test

### 3. Import dashboard

**Dashboard panels:**

**Token Usage:**
```promql
sum(rate(llm_tokens_total[5m])) by (type)
```

**Cost per Hour:**
```promql
rate(llm_cost_dollars_total[1h]) * 3600
```

**P95 Latency:**
```promql
histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m]))
```

**Error Rate:**
```promql
rate(http_errors_total[5m]) / rate(request_latency_seconds_count[5m]) * 100
```

**User Satisfaction:**
```promql
rate(user_feedback_total{sentiment="positive"}[1h]) / rate(user_feedback_total[1h]) * 100
```

---

## Alerts

**Example alerts.yml:**
```yaml
groups:
  - name: genai_auto
    interval: 1m
    rules:
      # Cost alert
      - alert: HighLLMCost
        expr: rate(llm_cost_dollars_total[1h]) > 10
        for: 5m
        annotations:
          summary: "LLM spend exceeds $10/hour"
      
      # Latency alert
      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(request_latency_seconds_bucket[5m])) > 5
        for: 5m
        annotations:
          summary: "P95 latency exceeds 5 seconds"
      
      # Error rate alert
      - alert: HighErrorRate
        expr: rate(http_errors_total[5m]) / rate(request_latency_seconds_count[5m]) > 0.05
        for: 5m
        annotations:
          summary: "Error rate exceeds 5%"
      
      # Low satisfaction alert
      - alert: LowUserSatisfaction
        expr: rate(user_feedback_total{sentiment="positive"}[1h]) / rate(user_feedback_total[1h]) < 0.6
        for: 15m
        annotations:
          summary: "User satisfaction below 60%"
```

---

## Best Practices

### 1. Token Counting

**Accurate counting (recommended):**
```python
import tiktoken

enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
tokens = len(enc.encode(text))
```

**Quick estimate:**
```python
tokens = len(text.split()) * 1.3
```

### 2. Cost Tracking

Update `MODEL_PRICING` in `metrics.py` when:
- Adding new models
- Pricing changes
- Using different providers

### 3. Sampling

For high-traffic apps, sample metrics:
```python
import random

if random.random() < 0.1:  # 10% sampling
    track_llm_call(...)
```

### 4. Cardinality

Avoid high-cardinality labels (e.g., don't use `user_id` as label). Use aggregation instead.

---

## Troubleshooting

**Metrics not appearing:**
1. Check `/api/v1/metrics` returns data
2. Verify Prometheus config points to correct URL
3. Check Prometheus targets: http://localhost:9090/targets

**High memory usage:**
- Reduce metric retention (default 15 days)
- Sample high-frequency metrics
- Use recording rules for complex queries

**Missing token counts:**
- Verify LLM provider returns usage data
- Add token counting library (tiktoken)
- Use estimation as fallback

---

## Next Steps

### Phase 2 Metrics (Advanced)

After implementing essentials, add:

6. **RAG Similarity Score** - Track retrieval quality
7. **Cache Hit Rate** - Monitor cache efficiency
8. **Handoff Rate** - Human escalation tracking
9. **Task Completion Rate** - Did user solve their problem?
10. **Agent Routing Accuracy** - Correct agent selection rate

See `docs/ADVANCED_METRICS.md` for implementation guide.

---

## Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Grafana Dashboards](https://grafana.com/grafana/dashboards/)
- [OpenTelemetry](https://opentelemetry.io/) - For distributed tracing
- [tiktoken](https://github.com/openai/tiktoken) - Token counting library
