# A/B Testing Guide

## Overview

A/B testing framework for GenAI Auto enables data-driven decisions about:
- Model selection (GPT-4 vs Claude vs Llama)
- Prompts and system messages
- Confidence thresholds
- Routing algorithms
- Cache strategies
- RAG configurations

**Key Features:**
- ✅ Consistent user assignment (hashing)
- ✅ Weighted traffic splitting
- ✅ Metrics integration (auto-tracking)
- ✅ Multi-variant support (A/B/C/...)
- ✅ Experiment lifecycle management

---

## Quick Start

### 1. Define Experiment

```python
from experiments import Experiment, Variant, ExperimentManager
from datetime import datetime, timedelta

experiment = Experiment(
    name="new_embedding_model",
    description="Test nomic-embed v2.0 vs v1.5",
    variants=[
        Variant(
            name="control",
            weight=0.5,  # 50% traffic
            config={"model": "nomic-ai/nomic-embed-text-v1.5"}
        ),
        Variant(
            name="treatment",
            weight=0.5,  # 50% traffic
            config={"model": "nomic-ai/nomic-embed-text-v2.0"}
        )
    ],
    end_date=datetime.now() + timedelta(days=7)  # Run for 7 days
)
```

### 2. Register & Start

```python
manager = ExperimentManager()
manager.register_experiment(experiment)
experiment.start()
```

### 3. Use in Code

```python
# Get variant for user
variant = manager.get_variant("new_embedding_model", user_id)

if variant:
    # Use variant config
    embedding_model = variant.config["model"]
    
    # Metrics tracked automatically with experiment labels
    track_rag_retrieval(
        agent="specs",
        similarity_scores=[0.89, 0.85],
        labels={
            "experiment": "new_embedding_model",
            "variant": variant.name
        }
    )
else:
    # Fallback to default (experiment not active)
    embedding_model = default_model
```

### 4. Analyze Results

```python
from experiments import ExperimentMetricsCollector

collector = ExperimentMetricsCollector()

# Compare variants
results = await collector.compare_variants(
    experiment_name="new_embedding_model",
    variant_names=["control", "treatment"],
    duration="7d"
)

# Results:
# {
#   "control": ExperimentMetrics(...),
#   "treatment": ExperimentMetrics(...)
# }

# Make decision
if results["treatment"].avg_similarity > results["control"].avg_similarity:
    print("✅ Treatment wins! Rolling out v2.0")
    # Promote treatment to 100%
else:
    print("❌ Control wins. Keeping v1.5")
```

---

## Experiment Examples

### Example 1: Test New LLM Model

```python
experiment = Experiment(
    name="llm_model_comparison",
    description="GPT-4 vs Claude Opus 4.6",
    variants=[
        Variant(
            name="gpt4",
            weight=0.5,
            config={
                "model": "openai/gpt-4",
                "temperature": 0.7
            }
        ),
        Variant(
            name="claude",
            weight=0.5,
            config={
                "model": "anthropic/claude-opus-4-6",
                "temperature": 0.7
            }
        )
    ]
)

# In chat endpoint:
variant = manager.get_variant("llm_model_comparison", user_id)
model = variant.config["model"]
temp = variant.config["temperature"]

response = await llm.generate(
    message=user_message,
    model=model,
    temperature=temp
)

track_llm_call(
    model=model,
    agent="specs",
    input_tokens=100,
    output_tokens=200,
    duration=2.5,
    labels={"experiment": "llm_model_comparison", "variant": variant.name}
)

# Compare:
# - Cost per request
# - Latency
# - User satisfaction
# - Error rate
```

### Example 2: Test Confidence Threshold

```python
experiment = Experiment(
    name="confidence_threshold",
    description="Test 0.6 vs 0.7 handoff threshold",
    variants=[
        Variant(name="threshold_60", weight=0.5, config={"threshold": 0.6}),
        Variant(name="threshold_70", weight=0.5, config={"threshold": 0.7})
    ]
)

# In session manager:
variant = manager.get_variant("confidence_threshold", user_id)
threshold = variant.config["threshold"]

if response.confidence < threshold:
    session.trigger_handoff(
        reason=HandoffReason.LOW_CONFIDENCE,
        confidence_score=response.confidence,
        labels={"experiment": "confidence_threshold", "variant": variant.name}
    )

# Compare:
# - Handoff rate
# - Task completion rate
# - User satisfaction
```

### Example 3: Test Cache TTL

```python
experiment = Experiment(
    name="cache_ttl",
    description="1 hour vs 24 hour TTL",
    variants=[
        Variant(name="ttl_1h", weight=0.5, config={"ttl": 3600}),
        Variant(name="ttl_24h", weight=0.5, config={"ttl": 86400})
    ]
)

# In cache service:
variant = manager.get_variant("cache_ttl", user_id)
ttl = variant.config["ttl"]

await cache.set(
    key=cache_key,
    value=embedding,
    ttl=ttl
)

track_cache_operation(
    operation="set",
    cache_type="embedding",
    latency_ms=2.5,
    labels={"experiment": "cache_ttl", "variant": variant.name}
)

# Compare:
# - Cache hit rate
# - Memory usage
# - Latency
```

### Example 4: Test RAG top_k

```python
experiment = Experiment(
    name="rag_top_k",
    description="Retrieve 3 vs 5 vs 7 documents",
    variants=[
        Variant(name="top_3", weight=0.33, config={"top_k": 3}),
        Variant(name="top_5", weight=0.34, config={"top_k": 5}),
        Variant(name="top_7", weight=0.33, config={"top_k": 7})
    ]
)

# In RAG retriever:
variant = manager.get_variant("rag_top_k", user_id)
top_k = variant.config["top_k"]

results = await retriever.retrieve(
    query=query,
    agent="specs",
    top_k=top_k
)

track_rag_retrieval(
    agent="specs",
    similarity_scores=[r.similarity for r in results],
    labels={"experiment": "rag_top_k", "variant": variant.name}
)

# Compare:
# - Average similarity
# - Latency
# - User satisfaction
# - Cost (more docs = more context = higher LLM cost)
```

---

## Metrics Comparison

### Prometheus Queries

**Latency by variant:**
```promql
avg by (variant) (
  rate(request_latency_seconds_sum{experiment="my_experiment"}[1h]) /
  rate(request_latency_seconds_count{experiment="my_experiment"}[1h])
)
```

**Cost by variant:**
```promql
sum by (variant) (
  rate(llm_cost_dollars_total{experiment="my_experiment"}[1h])
) * 3600
```

**Error rate by variant:**
```promql
sum by (variant) (
  rate(http_errors_total{experiment="my_experiment"}[1h])
) /
sum by (variant) (
  rate(request_latency_seconds_count{experiment="my_experiment"}[1h])
) * 100
```

**User satisfaction by variant:**
```promql
sum by (variant) (
  rate(user_feedback_total{sentiment="positive",experiment="my_experiment"}[1h])
) /
sum by (variant) (
  rate(user_feedback_total{experiment="my_experiment"}[1h])
) * 100
```

---

## Statistical Significance

### Sample Size Calculator

Before running experiment, calculate required sample size:

```python
from scipy import stats

def calculate_sample_size(
    baseline_rate: float,  # e.g., 0.75 (75% satisfaction)
    min_detectable_effect: float,  # e.g., 0.05 (5% improvement)
    alpha: float = 0.05,  # Significance level
    power: float = 0.80  # Statistical power
) -> int:
    """
    Calculate required sample size per variant.
    
    Args:
        baseline_rate: Current metric value (0-1)
        min_detectable_effect: Minimum change to detect (0-1)
        alpha: False positive rate (typically 0.05)
        power: True positive rate (typically 0.80)
    
    Returns:
        Required samples per variant
    """
    effect_size = min_detectable_effect / baseline_rate
    z_alpha = stats.norm.ppf(1 - alpha/2)
    z_beta = stats.norm.ppf(power)
    
    n = ((z_alpha + z_beta) ** 2) * (baseline_rate * (1 - baseline_rate)) / (min_detectable_effect ** 2)
    
    return int(n)

# Example:
# Current satisfaction: 75%
# Want to detect: 5% improvement (to 80%)
samples_needed = calculate_sample_size(0.75, 0.05)
print(f"Need {samples_needed} samples per variant")
# Output: Need ~385 samples per variant
```

### Significance Test

After collecting data, test if difference is significant:

```python
from scipy import stats

def is_significant(
    control_successes: int,
    control_total: int,
    treatment_successes: int,
    treatment_total: int,
    alpha: float = 0.05
) -> tuple[bool, float]:
    """
    Test if difference between variants is statistically significant.
    
    Returns:
        (is_significant, p_value)
    """
    # Two-proportion z-test
    z_stat, p_value = stats.proportions_ztest(
        [control_successes, treatment_successes],
        [control_total, treatment_total]
    )
    
    return p_value < alpha, p_value

# Example:
control_positive = 750   # 75% satisfaction
control_total = 1000
treatment_positive = 820  # 82% satisfaction
treatment_total = 1000

is_sig, p_val = is_significant(
    control_positive, control_total,
    treatment_positive, treatment_total
)

if is_sig:
    print(f"✅ Difference is significant (p={p_val:.4f})")
    print("Confident that treatment is better!")
else:
    print(f"❌ Not significant (p={p_val:.4f})")
    print("Need more data or difference is too small")
```

---

## Best Practices

### 1. Run Time

**Minimum:**
- Small changes (threshold tweak): 2-3 days
- Medium changes (model swap): 1 week
- Large changes (architecture): 2 weeks

**Why?**
- Account for day-of-week effects
- Collect sufficient samples
- Ensure statistical power

### 2. Traffic Split

**Conservative (new risky feature):**
- 90% control, 10% treatment
- Ramp up if successful

**Balanced (low risk):**
- 50% / 50% split

**Multi-variant:**
- 40% control, 30% variant A, 30% variant B

### 3. Metrics to Track

**Primary metric** (one per experiment):
- User satisfaction
- Task completion rate
- Cost per request

**Secondary metrics** (guardrails):
- Latency (don't regress)
- Error rate (don't increase)
- Cost (don't blow budget)

### 4. Decision Criteria

Define before experiment:

```python
# Example criteria
CRITERIA = {
    "primary_metric": {
        "name": "user_satisfaction",
        "threshold": 0.05,  # 5% improvement
        "direction": "increase"
    },
    "guardrails": [
        {"name": "latency", "max_regression": 0.10},  # 10% slower ok
        {"name": "error_rate", "max_increase": 0.02},  # 2% more errors ok
        {"name": "cost", "max_increase": 0.20}  # 20% more cost ok
    ]
}

# Winner if:
# - Primary metric improved by > 5%
# - All guardrails respected
```

### 5. Early Stopping

Stop experiment early if:
- ❌ **Safety issue** (high error rate, outage)
- ❌ **Budget exceeded** (cost runaway)
- ✅ **Clear winner** (p < 0.001, large effect)
- ✅ **No effect** (p > 0.5, zero change)

---

## Troubleshooting

### Metrics not separating by variant

**Problem:** All traffic showing as one variant

**Causes:**
- Experiment not started
- Variant assignment not working
- Metrics not tagged with experiment labels

**Fix:**
```python
# Check experiment status
experiment = manager.get_experiment("my_exp")
print(experiment.status)  # Should be RUNNING

# Check variant assignment
variant = manager.get_variant("my_exp", "test_user_123")
print(variant.name)  # Should return variant

# Verify metrics have labels
track_llm_call(
    model="gpt-4",
    agent="specs",
    input_tokens=100,
    output_tokens=200,
    duration=2.5,
    labels={  # ← REQUIRED
        "experiment": "my_exp",
        "variant": variant.name
    }
)
```

### Inconsistent assignments

**Problem:** Same user gets different variants

**Cause:** User ID not stable (e.g., using session ID instead)

**Fix:**
```python
# Use stable identifier
user_id = request.user.id  # ✅ Stable
# NOT: user_id = session_id  # ❌ Changes

variant = manager.get_variant("exp", user_id)
```

### Not enough data

**Problem:** Can't determine winner after 7 days

**Fix:**
- Run longer (14-30 days)
- Increase traffic allocation
- Accept smaller effect size
- Use different primary metric

---

## Advanced Features

### Gradual Rollout

Start with 10%, increase if successful:

```python
# Week 1: 90/10 split
variants = [
    Variant(name="control", weight=0.9, config=...),
    Variant(name="treatment", weight=0.1, config=...)
]

# Week 2: If good, 50/50
experiment.variants[0].weight = 0.5
experiment.variants[1].weight = 0.5

# Week 3: If great, 100% treatment
experiment.variants[0].weight = 0.0
experiment.variants[1].weight = 1.0

# Or just complete experiment
experiment.complete()
# Remove variant logic from code
```

### Interaction Effects

Test combinations:

```python
# Experiment 1: Model
model_exp = Experiment(name="model", variants=[...])

# Experiment 2: Threshold
threshold_exp = Experiment(name="threshold", variants=[...])

# User gets variant from EACH experiment
model_variant = manager.get_variant("model", user_id)
threshold_variant = manager.get_variant("threshold", user_id)

# 2x2 = 4 combinations tested simultaneously
```

---

## Resources

- [Statsmodels (Python)](https://www.statsmodels.org/)
- [A/B Testing Statistics](https://www.evanmiller.org/ab-testing/)
- [Sample Size Calculator](https://www.evanmiller.org/ab-testing/sample-size.html)
- [Experiment Design Guide](https://experimentguide.com/)

---

## Next Steps

1. ✅ Set up A/B testing framework
2. ✅ Define first experiment
3. ✅ Implement variant assignment
4. ✅ Add experiment labels to metrics
5. ✅ Run for minimum duration
6. ✅ Analyze results
7. ✅ Make data-driven decision
8. 🔄 Iterate!
