# ML Observability Guide

## Overview

ML Observability monitors model performance over time to detect:
- **Model drift** - Performance degradation
- **Data drift** - Input distribution changes
- **Concept drift** - Relationship between inputs and outputs changes

**Why it matters:**
- Models degrade over time
- User behavior shifts
- Data patterns change
- Early detection prevents poor UX

---

## Model Drift Detection

### What is Model Drift?

Performance metrics change significantly compared to baseline:

| Metric | Baseline | Current | Change | Status |
|--------|----------|---------|--------|--------|
| RAG Similarity | 0.82 | 0.70 | -15% | ⚠️ WARNING |
| Completion Rate | 0.75 | 0.52 | -31% | 🔴 CRITICAL |
| Avg Latency | 1.5s | 2.1s | +40% | 🔴 CRITICAL |
| Error Rate | 2% | 2.4% | +20% | ✅ NORMAL |

### Monitored Metrics

**Quality metrics (↓ is bad):**
- RAG similarity score
- Cache hit rate
- Task completion rate
- Routing confidence

**Cost/Performance metrics (↑ is bad):**
- Average latency
- Error rate
- Handoff rate
- LLM cost per request

---

## Quick Start

### 1. Initialize Monitor

```python
from observability import PerformanceMonitor

monitor = PerformanceMonitor(
    prometheus_url="http://localhost:9090"
)
```

### 2. Collect Baseline

Run once to establish baseline (typically 7-day average):

```python
# Collect baseline from last 7 days
await monitor.collect_baseline(lookback_days=7)

# Baselines stored:
# - avg_similarity: 0.82
# - cache_hit_rate: 0.65
# - completion_rate: 0.75
# - routing_confidence: 0.85
# - avg_latency: 1.5s
# - error_rate: 0.02
# - handoff_rate: 0.10
# - avg_cost: $0.05
```

### 3. Check for Drift

Run periodically (hourly or daily):

```python
# Check current metrics vs baseline
drifts = await monitor.check_drift()

if drifts:
    # Generate human-readable report
    report = monitor.generate_report(drifts)
    print(report)
    
    # Send to Slack
    await send_slack_message(report)
    
    # Save to file
    with open("drift-report.md", "w") as f:
        f.write(report)
```

### 4. Sample Report

```markdown
# Model Drift Report

Generated: 2024-01-15 14:30:00

## 🔴 CRITICAL Drifts

- **completion_rate**: Task completion rate has decreased by 30.7% (baseline: 0.750, current: 0.520)
- **avg_latency**: Average latency has increased by 40.0% (baseline: 1.500, current: 2.100)
- **avg_cost**: LLM cost has increased by 40.0% (baseline: 0.050, current: 0.070)

## ⚠️ WARNING Drifts

- **avg_similarity**: RAG similarity has decreased by 14.6% (baseline: 0.820, current: 0.700)

## Recommendations

**Immediate action required:**
- Investigate completion_rate degradation (Task success rate)
- Investigate avg_latency spike (Response speed)
- Investigate avg_cost spike (LLM spend)

**Monitor closely:**
- Watch avg_similarity trend
```

---

## Manual Drift Detection

For custom metrics:

```python
from observability import ModelDriftDetector

detector = ModelDriftDetector(
    warning_threshold=0.15,  # 15% change triggers warning
    critical_threshold=0.30  # 30% change triggers critical
)

# Set baseline
detector.set_baseline("user_satisfaction", 0.80)

# Later... check current value
drift = detector.check_drift("user_satisfaction", 0.65)

if drift:
    print(f"{drift.severity.value}: {drift.message}")
    # Output: "warning: user_satisfaction has decreased by 18.8%"
```

---

## Automated Monitoring

### Cron Job (Daily Check)

**Script:** `scripts/check_drift.py`

```python
#!/usr/bin/env python3
"""
Daily drift check - runs via cron.
"""

import asyncio
from observability import PerformanceMonitor
from datetime import datetime

async def main():
    monitor = PerformanceMonitor()
    
    # Check for drift
    drifts = await monitor.check_drift()
    
    if not drifts:
        print("✅ No drift detected")
        return 0
    
    # Generate report
    report = monitor.generate_report(drifts)
    
    # Save to file
    filename = f"drift-report-{datetime.now():%Y%m%d}.md"
    with open(filename, "w") as f:
        f.write(report)
    
    # Send alert if critical
    critical = [d for d in drifts if d.severity.value == "critical"]
    if critical:
        # Send to Slack/PagerDuty
        await send_critical_alert(report)
        return 1  # Exit code 1 for critical drift
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))
```

**Crontab:**
```bash
# Check drift daily at 9 AM
0 9 * * * cd /path/to/genai-auto && python scripts/check_drift.py
```

### Prometheus Alert (Real-time)

Add to `alerts.yml`:

```yaml
- alert: ModelDriftDetected
  expr: |
    (
      avg(rag_similarity_score) < 0.70
      OR
      rate(task_completion_total{status="completed"}[1h]) / 
      rate(task_completion_total[1h]) < 0.65
      OR
      avg(rate(request_latency_seconds_sum[1h]) / 
          rate(request_latency_seconds_count[1h])) > 2.0
    )
  for: 1h
  labels:
    severity: warning
  annotations:
    summary: "Potential model drift detected"
    description: "Key metrics have degraded significantly"
```

---

## Drift Analysis

### Trending

Track metrics over time:

**Grafana query:**
```promql
# 7-day moving average
avg_over_time(rag_similarity_score[7d])

# Compare to baseline (0.82)
(avg(rag_similarity_score) - 0.82) / 0.82 * 100
# Returns: percent change from baseline
```

### Segmentation

Analyze drift by dimension:

**By agent:**
```promql
avg by (agent) (rag_similarity_score)
# Which agent is degrading?
```

**By time:**
```promql
avg_over_time(rag_similarity_score[1h])
# When did drift start?
```

**By user cohort:**
```promql
avg by (user_tier) (
  rate(task_completion_total{status="completed"}[1h]) /
  rate(task_completion_total[1h])
)
# Are premium users affected more?
```

---

## Root Cause Analysis

### Common Causes

**1. Model drift:**
- Model hasn't been retrained
- Training data is stale
- Model version changed

**Fix:**
- Retrain with recent data
- A/B test new model version
- Roll back if recent deploy

**2. Data drift:**
- User behavior changed
- New user segment
- Seasonal effects

**Fix:**
- Update training data
- Adjust confidence thresholds
- Create user segments

**3. Infrastructure:**
- Database slow
- Cache cold
- Network issues

**Fix:**
- Scale resources
- Warm cache
- Check service health

**4. External dependencies:**
- LLM provider issues
- Embeddings API slow
- Vector DB degraded

**Fix:**
- Switch provider
- Use fallback
- Increase timeouts

### Diagnostic Queries

**Is it everywhere or specific?**
```promql
# Overall drift
avg(rag_similarity_score)

# By agent
avg by (agent) (rag_similarity_score)

# By document type
avg by (document_type) (rag_similarity_score)
```

**When did it start?**
```promql
# Plot over last 7 days
avg_over_time(rag_similarity_score[7d:1h])
```

**Is it getting worse?**
```promql
# Rate of change (derivative)
deriv(avg_over_time(rag_similarity_score[1h])[5m:])
```

---

## Thresholds

### Default Thresholds

| Metric | Warning | Critical |
|--------|---------|----------|
| RAG Similarity | -15% | -30% |
| Cache Hit Rate | -15% | -30% |
| Completion Rate | -15% | -30% |
| Routing Confidence | -15% | -30% |
| Latency | +20% | +40% |
| Error Rate | +30% | +50% |
| Handoff Rate | +25% | +50% |
| Cost | +20% | +40% |

### Custom Thresholds

Adjust based on your requirements:

```python
detector = ModelDriftDetector(
    warning_threshold=0.10,  # 10% (more sensitive)
    critical_threshold=0.20  # 20%
)
```

**Considerations:**
- **Too sensitive** → Alert fatigue, false positives
- **Too loose** → Miss real issues
- **Sweet spot** → ~15% warning, ~30% critical

---

## Retraining Strategy

### When to Retrain

**Criteria:**
- Critical drift detected (>30% degradation)
- Multiple metrics degraded
- Drift persists > 3 days
- User satisfaction drops

**Frequency:**
- **Proactive**: Monthly or quarterly
- **Reactive**: When drift detected
- **Continuous**: For production ML systems

### How to Retrain

1. **Collect recent data** (last 30-90 days)
2. **Validate data quality**
3. **Retrain model**
4. **A/B test** new vs old model
5. **Roll out** if successful
6. **Update baseline**

### Example

```python
# After retraining and A/B testing
if new_model_wins:
    # Update baseline with new model's performance
    await monitor.collect_baseline(lookback_days=7)
    
    # Reset drift detector
    monitor.drift_detector = ModelDriftDetector()
    
    print("✅ Baseline updated with retrained model")
```

---

## Best Practices

### 1. Set Baseline Properly

**Do:**
- Use 7-14 day average
- Exclude outliers/incidents
- Update after major changes

**Don't:**
- Use single day
- Include downtime periods
- Set arbitrary values

### 2. Monitor Holistically

**Don't just track one metric:**
- RAG similarity alone doesn't tell full story
- Check multiple correlated metrics
- Look for patterns

**Example:**
```
RAG similarity down ↓
+ Completion rate down ↓
+ Handoff rate up ↑
= Users struggling to find answers → Knowledge base issue
```

### 3. Act on Alerts

**Prioritize:**
1. **Critical drift** → Immediate action
2. **Multiple warnings** → Investigate soon
3. **Single warning** → Monitor

**Document:**
- What drifted
- When detected
- Root cause
- Fix applied
- Baseline updated

### 4. Regular Reviews

**Weekly:**
- Review drift reports
- Check trend dashboards
- Update thresholds if needed

**Monthly:**
- Analyze drift patterns
- Evaluate retraining needs
- Update monitoring strategy

---

## Troubleshooting

### False Positives

**Problem:** Alerts for non-issues

**Causes:**
- Thresholds too sensitive
- Natural variance
- Temporary spike

**Fix:**
```python
# Increase thresholds
detector = ModelDriftDetector(
    warning_threshold=0.20,  # Was 0.15
    critical_threshold=0.40  # Was 0.30
)

# Or require sustained drift
# Only alert if drift persists > 2 hours
```

### Missed Drift

**Problem:** Degradation not detected

**Causes:**
- Thresholds too loose
- Baseline stale
- Wrong metrics

**Fix:**
- Lower thresholds
- Update baseline regularly
- Add more metrics
- Check baseline calculation

### Noisy Metrics

**Problem:** Metric fluctuates wildly

**Causes:**
- Low traffic
- Outliers
- Time-of-day effects

**Fix:**
```promql
# Use moving average instead of instant value
avg_over_time(rag_similarity_score[1h])

# Or median (more robust to outliers)
quantile(0.5, rag_similarity_score)
```

---

## Advanced Topics

### Multi-Modal Drift

Different metrics drift at different rates:

```python
# Weight metrics by importance
weights = {
    "completion_rate": 0.4,  # Most important
    "avg_similarity": 0.3,
    "routing_confidence": 0.2,
    "error_rate": 0.1
}

# Calculate weighted drift score
drift_score = sum(
    weights[metric] * abs(drift.percent_change)
    for metric, drift in drifts.items()
)

if drift_score > 25:  # 25% weighted average drift
    print("🔴 Significant multi-modal drift detected")
```

### Seasonal Adjustment

Account for day-of-week or time-of-day patterns:

```python
# Compare Monday to Monday (not Monday to Friday)
baseline_monday = get_baseline(weekday=0)  # 0 = Monday
current_monday = get_current(weekday=0)

drift = detector.check_drift(
    "completion_rate",
    current_monday,
    baseline_value=baseline_monday
)
```

### Drift Velocity

Track how fast drift is occurring:

```python
# Measure week-over-week change
last_week = 0.75
this_week = 0.70
drift_velocity = (this_week - last_week) / last_week

if drift_velocity < -0.10:  # -10% per week
    print("⚠️ Rapid degradation - investigate immediately")
```

---

## Resources

- [Evidently AI](https://www.evidentlyai.com/) - ML monitoring
- [Arize AI](https://arize.com/) - Model observability
- [WhyLabs](https://whylabs.ai/) - Data and ML monitoring
- [MLflow](https://mlflow.org/) - ML lifecycle management

---

## Next Steps

1. ✅ Set up PerformanceMonitor
2. ✅ Collect baseline metrics
3. ✅ Schedule daily drift checks
4. ✅ Create drift alerts
5. ✅ Document retraining process
6. 🔄 Monitor and iterate!
