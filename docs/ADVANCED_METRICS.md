# Advanced Metrics Guide (Phase 2)

This guide covers the 5 advanced metrics that complement the [essential metrics](METRICS.md).

## Overview

Advanced metrics provide deeper insights into:
- **RAG quality** - Are retrievals relevant?
- **Cache efficiency** - Is caching working?
- **Support escalation** - When and why do we handoff?
- **User success** - Do users complete their tasks?
- **Routing quality** - Are messages going to the right agent?

---

## 6. RAG Similarity Score

### What It Measures

Semantic similarity between user query and retrieved documents.

**Higher score = Better retrieval quality**

### Metrics

```
rag_similarity_score (histogram)
  - labels: agent, document_type
  - buckets: [0.0, 0.3, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

rag_documents_retrieved_total (counter)
  - labels: agent, document_type

rag_search_latency_ms (histogram)
  - labels: agent
  - buckets: [10, 25, 50, 100, 200, 500, 1000, 2000]
```

### Integration

```python
from api.metrics import track_rag_retrieval

# After vector search
results = await vector_store.similarity_search(query, k=5)

track_rag_retrieval(
    agent="specs",
    document_type="manual",
    similarity_scores=[r.similarity for r in results],
    search_latency_ms=search_time_ms
)
```

### Queries

**Average similarity score:**
```promql
avg(rag_similarity_score)
```

**Similarity by agent:**
```promql
avg by (agent) (rag_similarity_score)
```

**Low similarity rate (< 0.7):**
```promql
sum(rate(rag_similarity_score_bucket{le="0.7"}[5m])) / 
sum(rate(rag_similarity_score_count[5m]))
```

**Search latency P95:**
```promql
histogram_quantile(0.95, rate(rag_search_latency_ms_bucket[5m]))
```

### Alerts

```yaml
- alert: LowRAGSimilarity
  expr: avg(rag_similarity_score) < 0.6
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "RAG retrieval quality is low"
    description: "Average similarity score below 0.6 (current: {{ $value }})"
```

### Interpretation

| Score Range | Quality | Action |
|------------|---------|--------|
| 0.9 - 1.0 | Excellent | Keep monitoring |
| 0.8 - 0.9 | Good | Normal operation |
| 0.7 - 0.8 | Fair | Consider tuning embeddings |
| 0.6 - 0.7 | Poor | Review chunking strategy |
| < 0.6 | Very Poor | Knowledge base gaps or embedding issues |

---

## 7. Cache Hit Rate

### What It Measures

Percentage of requests served from cache vs. generated fresh.

**Higher hit rate = Better performance & lower cost**

### Metrics

```
cache_operations_total (counter)
  - labels: operation (hit/miss), cache_type (response/embedding)

cache_latency_ms (histogram)
  - labels: operation, cache_type
  - buckets: [1, 5, 10, 25, 50, 100, 200]
```

### Integration

```python
from api.metrics import track_cache_operation

# Cache hit
cached = await cache.get(key)
if cached:
    track_cache_operation(
        operation="hit",
        cache_type="embedding",
        latency_ms=get_time_ms
    )
    return cached

# Cache miss
result = await generate_embedding(text)
track_cache_operation(
    operation="miss",
    cache_type="embedding",
    latency_ms=get_time_ms
)

await cache.set(key, result, ttl=3600)
return result
```

### Queries

**Cache hit rate:**
```promql
rate(cache_operations_total{operation="hit"}[5m]) / 
rate(cache_operations_total[5m]) * 100
```

**Hit rate by cache type:**
```promql
sum by (cache_type) (
  rate(cache_operations_total{operation="hit"}[5m])
) / 
sum by (cache_type) (
  rate(cache_operations_total[5m])
) * 100
```

**Cache latency P95 (hit vs miss):**
```promql
histogram_quantile(0.95, 
  sum by (operation, le) (
    rate(cache_latency_ms_bucket[5m])
  )
)
```

**Misses per hour:**
```promql
rate(cache_operations_total{operation="miss"}[1h]) * 3600
```

### Alerts

```yaml
- alert: LowCacheHitRate
  expr: |
    rate(cache_operations_total{operation="hit"}[15m]) / 
    rate(cache_operations_total[15m]) < 0.5
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Cache hit rate below 50%"
    description: "Hit rate: {{ $value | humanizePercentage }}"

- alert: HighCacheLatency
  expr: |
    histogram_quantile(0.95, rate(cache_latency_ms_bucket[5m])) > 100
  for: 5m
  labels:
    severity: warning
  annotations:
    summary: "High cache latency detected"
```

### Interpretation

| Hit Rate | Status | Action |
|----------|--------|--------|
| > 80% | Excellent | Optimal caching |
| 60-80% | Good | Working as expected |
| 40-60% | Fair | Review TTL settings |
| < 40% | Poor | Cache config or traffic pattern issue |

**Note:** Hit rate depends heavily on traffic patterns. Repeated queries → high hit rate. Unique queries → low hit rate.

---

## 8. Handoff Rate

### What It Measures

How often conversations escalate to human support.

**Lower rate (with high satisfaction) = Better AI performance**

### Metrics

```
human_handoff_total (counter)
  - labels: reason (low_confidence/user_request/safety/error), agent

handoff_confidence_score (histogram)
  - buckets: [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0]
```

### Integration

```python
from api.metrics import track_human_handoff

# Confidence-based handoff
if response.confidence < 0.7:
    track_human_handoff(
        reason="low_confidence",
        agent="specs",
        confidence_score=response.confidence
    )
    return escalate_to_human()

# User-requested handoff
if "talk to human" in message.lower():
    track_human_handoff(
        reason="user_request",
        agent=current_agent,
        confidence_score=None
    )
    return connect_to_agent()

# Safety-triggered handoff
if safety_issue_detected():
    track_human_handoff(
        reason="safety",
        agent=current_agent,
        confidence_score=None
    )
    return emergency_escalation()
```

### Queries

**Handoff rate (per hour):**
```promql
rate(human_handoff_total[1h]) * 3600
```

**Handoff rate percentage (of total conversations):**
```promql
rate(human_handoff_total[1h]) / 
rate(request_latency_seconds_count{endpoint="/api/v1/chat"}[1h]) * 100
```

**Handoffs by reason:**
```promql
sum by (reason) (rate(human_handoff_total[1h])) * 3600
```

**Average confidence at handoff:**
```promql
avg(handoff_confidence_score)
```

**Most problematic agent (highest handoff):**
```promql
topk(1, sum by (agent) (rate(human_handoff_total[1h])))
```

### Alerts

```yaml
- alert: HighHandoffRate
  expr: |
    rate(human_handoff_total[1h]) / 
    rate(request_latency_seconds_count{endpoint="/api/v1/chat"}[1h]) > 0.2
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Handoff rate exceeds 20%"
    description: "Current: {{ $value | humanizePercentage }}"

- alert: FrequentLowConfidenceHandoffs
  expr: rate(human_handoff_total{reason="low_confidence"}[15m]) > 10
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "Frequent low-confidence handoffs"
    description: "More than 10 per 15 minutes"
```

### Interpretation

| Handoff Rate | Status | Action |
|--------------|--------|--------|
| < 5% | Excellent | AI handling most requests |
| 5-10% | Good | Normal for complex domains |
| 10-20% | Fair | Review confidence thresholds |
| 20-30% | Poor | Model or prompt improvements needed |
| > 30% | Critical | Fundamental AI quality issue |

**By reason:**
- **low_confidence** → Model tuning, better prompts, or lower threshold
- **user_request** → Normal, respect user preference
- **safety** → Critical, must always escalate
- **error** → Technical issues, needs debugging

---

## 9. Task Completion Rate

### What It Measures

Percentage of user tasks that reach successful completion.

**Higher completion = Better UX**

### Metrics

```
task_completion_total (counter)
  - labels: status (completed/abandoned/escalated), agent

task_duration_seconds (histogram)
  - labels: agent, status
  - buckets: [10, 30, 60, 120, 300, 600, 1200, 1800]
```

### Integration

```python
from api.metrics import track_task_completion
import time

class ChatSession:
    def __init__(self, session_id: str, agent: str):
        self.session_id = session_id
        self.agent = agent
        self.start_time = time.time()
    
    def complete(self, status: str):
        """
        Status values:
        - completed: User achieved their goal
        - abandoned: User left without completing
        - escalated: Handed off to human
        """
        duration = time.time() - self.start_time
        
        track_task_completion(
            status=status,
            agent=self.agent,
            duration_seconds=duration
        )

# Usage
session = ChatSession("sess_123", "maintenance")
# ... conversation happens ...

# When done:
if user_achieved_goal():
    session.complete("completed")
elif escalated_to_human():
    session.complete("escalated")
else:
    session.complete("abandoned")
```

### Queries

**Completion rate:**
```promql
rate(task_completion_total{status="completed"}[1h]) / 
rate(task_completion_total[1h]) * 100
```

**Completion rate by agent:**
```promql
sum by (agent) (
  rate(task_completion_total{status="completed"}[1h])
) / 
sum by (agent) (
  rate(task_completion_total[1h])
) * 100
```

**Abandonment rate:**
```promql
rate(task_completion_total{status="abandoned"}[1h]) / 
rate(task_completion_total[1h]) * 100
```

**Average task duration (completed only):**
```promql
avg(task_duration_seconds{status="completed"})
```

**P95 task duration:**
```promql
histogram_quantile(0.95, 
  rate(task_duration_seconds_bucket{status="completed"}[5m])
)
```

### Alerts

```yaml
- alert: LowTaskCompletionRate
  expr: |
    rate(task_completion_total{status="completed"}[1h]) / 
    rate(task_completion_total[1h]) < 0.6
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "Task completion rate below 60%"
    description: "Current: {{ $value | humanizePercentage }}"

- alert: HighAbandonmentRate
  expr: |
    rate(task_completion_total{status="abandoned"}[1h]) / 
    rate(task_completion_total[1h]) > 0.3
  for: 30m
  labels:
    severity: warning
  annotations:
    summary: "High abandonment rate detected"
```

### Interpretation

| Completion Rate | Status | Action |
|-----------------|--------|--------|
| > 80% | Excellent | Users achieving goals |
| 70-80% | Good | Normal performance |
| 60-70% | Fair | Some UX friction |
| 50-60% | Poor | Significant UX issues |
| < 50% | Critical | Major problems with flow |

**Causes of low completion:**
- High latency (users get impatient)
- Inaccurate responses (users give up)
- Complex UI/flow (confusion)
- Technical errors

---

## 10. Agent Routing Accuracy

### What It Measures

How well the orchestrator routes messages to the right agent.

**Higher accuracy = Better first-contact resolution**

### Metrics

```
agent_routing_total (counter)
  - labels: selected_agent, routing_method (intent_classification/rule_based/fallback)

agent_routing_confidence (histogram)
  - labels: selected_agent
  - buckets: [0.0, 0.5, 0.6, 0.7, 0.75, 0.8, 0.85, 0.9, 0.95, 1.0]

agent_rerouting_total (counter)
  - labels: from_agent, to_agent, reason (wrong_agent/fallback/escalation)
```

### Integration

```python
from api.metrics import track_agent_routing, track_agent_rerouting

# Initial routing
async def route_message(message: str):
    intent, confidence = await classify_intent(message)
    
    # Determine routing method
    if confidence > 0.8:
        method = "intent_classification"
    elif confidence > 0.5:
        method = "rule_based"
    else:
        method = "fallback"
    
    selected_agent = intent_to_agent(intent)
    
    track_agent_routing(
        selected_agent=selected_agent,
        routing_method=method,
        confidence_score=confidence
    )
    
    return selected_agent

# Rerouting (when wrong agent detected)
if agent_realizes_wrong_task():
    track_agent_rerouting(
        from_agent="maintenance",
        to_agent="specs",
        reason="wrong_agent"
    )
    return reroute_to("specs")
```

### Queries

**Routing by method:**
```promql
sum by (routing_method) (rate(agent_routing_total[1h])) * 3600
```

**High-confidence routing rate:**
```promql
sum(rate(agent_routing_confidence_bucket{le="0.8"}[5m])) / 
sum(rate(agent_routing_confidence_count[5m])) * 100
```

**Rerouting rate (indication of errors):**
```promql
rate(agent_rerouting_total[5m])
```

**Most common routing errors:**
```promql
topk(3, sum by (from_agent, to_agent) (
  rate(agent_rerouting_total{reason="wrong_agent"}[1h])
))
```

**Average routing confidence:**
```promql
avg(agent_routing_confidence)
```

### Alerts

```yaml
- alert: LowRoutingConfidence
  expr: avg(agent_routing_confidence) < 0.7
  for: 15m
  labels:
    severity: warning
  annotations:
    summary: "Low routing confidence detected"
    description: "Average confidence: {{ $value }}"

- alert: HighReroutingRate
  expr: rate(agent_rerouting_total{reason="wrong_agent"}[15m]) > 0.1
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High rerouting rate (routing errors)"
    description: "More than 10% of routes need correction"
```

### Interpretation

| Metric | Good | Poor | Meaning |
|--------|------|------|---------|
| Avg Confidence | > 0.8 | < 0.6 | Classifier quality |
| Rerouting Rate | < 5% | > 15% | Initial routing accuracy |
| High-Conf Rate | > 70% | < 50% | Clear intent detection |

**Routing methods:**
- **intent_classification** (best) - High confidence, ML-based
- **rule_based** (ok) - Medium confidence, keyword matching
- **fallback** (worst) - Low confidence, default agent

**Improvement strategies:**
- Train better intent classifier
- Add more training examples
- Improve prompt for classification
- Review fallback rules

---

## Dashboard Queries

### Overview Panel

```promql
# Metrics summary
avg(rag_similarity_score)                                    # RAG quality
rate(cache_operations_total{operation="hit"}[5m]) / 
  rate(cache_operations_total[5m])                           # Cache hit %
rate(human_handoff_total[1h]) * 3600                         # Handoffs/hour
rate(task_completion_total{status="completed"}[1h]) / 
  rate(task_completion_total[1h])                            # Completion %
avg(agent_routing_confidence)                                # Routing confidence
```

### Performance Panel

```promql
# Latencies
histogram_quantile(0.95, rate(rag_search_latency_ms_bucket[5m]))
histogram_quantile(0.95, rate(cache_latency_ms_bucket{operation="hit"}[5m]))
histogram_quantile(0.95, rate(task_duration_seconds_bucket[5m]))
```

### Quality Panel

```promql
# Quality metrics
sum(rate(rag_similarity_score_bucket{le="0.7"}[5m])) / 
  sum(rate(rag_similarity_score_count[5m]))                  # Low similarity %
rate(agent_rerouting_total{reason="wrong_agent"}[5m])        # Routing errors/s
rate(human_handoff_total{reason="low_confidence"}[5m])       # Low conf handoffs/s
```

---

## Best Practices

### 1. Baseline First

Before optimizing, establish baselines:
- Run for 1 week with metrics enabled
- Identify "normal" values for your use case
- Set alerts based on your baselines, not generic thresholds

### 2. Correlate Metrics

Don't look at metrics in isolation:
- Low RAG similarity + High handoff rate → Knowledge base gaps
- High cache miss + High latency → Need bigger cache
- Low routing confidence + High rerouting → Classifier needs training
- High abandonment + High latency → Performance issue

### 3. Segmentation

Analyze by dimensions:
- By agent (which agent struggles most?)
- By time (performance degradation over time?)
- By document type (which docs have low retrieval quality?)

### 4. A/B Testing

Use metrics to validate changes:
- New embedding model → Compare RAG similarity
- New routing logic → Compare rerouting rate
- Cache TTL change → Compare hit rate

### 5. User Feedback Loop

Cross-reference with user feedback:
- High similarity but negative feedback → Irrelevant docs
- Low confidence but positive feedback → Threshold too high
- High completion rate + High satisfaction → Optimal state

---

## Next Steps

After implementing advanced metrics:

1. **Grafana Dashboard** - Visualize all 10 metrics
2. **Alertmanager** - Set up notifications (Slack/PagerDuty/Email)
3. **Automated Remediation** - Auto-scale cache, retrain models
4. **ML Observability** - Track model drift, feature importance
5. **Custom Metrics** - Domain-specific KPIs

---

## Resources

- [Prometheus Histograms](https://prometheus.io/docs/practices/histograms/)
- [Grafana Best Practices](https://grafana.com/docs/grafana/latest/best-practices/)
- [OpenTelemetry](https://opentelemetry.io/) - For distributed tracing
- [MLOps Best Practices](https://ml-ops.org/)
