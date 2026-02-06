"""
A/B Testing framework for GenAI experiments with metrics tracking.
"""

import hashlib
import random
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
from datetime import datetime, timedelta


class ExperimentStatus(Enum):
    """Experiment status."""
    DRAFT = "draft"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Variant:
    """
    A/B test variant.
    """
    name: str
    weight: float  # 0.0 - 1.0 (percentage allocation)
    config: Dict[str, Any]  # Configuration for this variant
    
    def __post_init__(self):
        if not (0 <= self.weight <= 1.0):
            raise ValueError("Weight must be between 0 and 1")


@dataclass
class ExperimentMetrics:
    """Aggregated metrics for a variant."""
    variant_name: str
    users: int = 0
    requests: int = 0
    
    # Essential metrics
    avg_latency: float = 0.0
    avg_cost: float = 0.0
    error_rate: float = 0.0
    positive_feedback_rate: float = 0.0
    
    # Advanced metrics
    avg_similarity: float = 0.0
    cache_hit_rate: float = 0.0
    handoff_rate: float = 0.0
    completion_rate: float = 0.0
    routing_confidence: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dict for comparison."""
        return {
            "variant": self.variant_name,
            "users": self.users,
            "requests": self.requests,
            "avg_latency": self.avg_latency,
            "avg_cost": self.avg_cost,
            "error_rate": self.error_rate,
            "positive_feedback_rate": self.positive_feedback_rate,
            "avg_similarity": self.avg_similarity,
            "cache_hit_rate": self.cache_hit_rate,
            "handoff_rate": self.handoff_rate,
            "completion_rate": self.completion_rate,
            "routing_confidence": self.routing_confidence,
        }


class Experiment:
    """
    A/B test experiment.
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        variants: List[Variant],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ):
        self.name = name
        self.description = description
        self.variants = variants
        self.start_date = start_date or datetime.now()
        self.end_date = end_date
        self.status = ExperimentStatus.DRAFT
        
        # Validate weights sum to 1.0
        total_weight = sum(v.weight for v in variants)
        if not (0.99 <= total_weight <= 1.01):  # Allow small float errors
            raise ValueError(f"Variant weights must sum to 1.0 (got {total_weight})")
    
    def assign_variant(self, user_id: str) -> Variant:
        """
        Assign user to variant using consistent hashing.
        
        Args:
            user_id: User identifier
        
        Returns:
            Assigned variant
        """
        # Hash user_id to get consistent assignment
        hash_value = int(hashlib.md5(f"{self.name}:{user_id}".encode()).hexdigest(), 16)
        random.seed(hash_value)
        rand = random.random()
        
        # Assign based on weights
        cumulative = 0.0
        for variant in self.variants:
            cumulative += variant.weight
            if rand <= cumulative:
                return variant
        
        # Fallback (should never reach here)
        return self.variants[0]
    
    def start(self):
        """Start experiment."""
        self.status = ExperimentStatus.RUNNING
        self.start_date = datetime.now()
    
    def pause(self):
        """Pause experiment."""
        self.status = ExperimentStatus.PAUSED
    
    def resume(self):
        """Resume paused experiment."""
        if self.status == ExperimentStatus.PAUSED:
            self.status = ExperimentStatus.RUNNING
    
    def complete(self):
        """Mark experiment as completed."""
        self.status = ExperimentStatus.COMPLETED
        self.end_date = datetime.now()
    
    def is_active(self) -> bool:
        """Check if experiment is currently active."""
        if self.status != ExperimentStatus.RUNNING:
            return False
        
        now = datetime.now()
        
        if now < self.start_date:
            return False
        
        if self.end_date and now > self.end_date:
            return False
        
        return True


class ExperimentManager:
    """
    Manages multiple A/B test experiments.
    """
    
    def __init__(self):
        self.experiments: Dict[str, Experiment] = {}
    
    def register_experiment(self, experiment: Experiment):
        """Register new experiment."""
        self.experiments[experiment.name] = experiment
    
    def get_variant(self, experiment_name: str, user_id: str) -> Optional[Variant]:
        """
        Get variant for user in experiment.
        
        Args:
            experiment_name: Name of experiment
            user_id: User identifier
        
        Returns:
            Assigned variant or None if experiment not active
        """
        experiment = self.experiments.get(experiment_name)
        
        if not experiment or not experiment.is_active():
            return None
        
        return experiment.assign_variant(user_id)
    
    def get_experiment(self, name: str) -> Optional[Experiment]:
        """Get experiment by name."""
        return self.experiments.get(name)


# ============================================================================
# METRICS COLLECTION
# ============================================================================

class ExperimentMetricsCollector:
    """
    Collects metrics from Prometheus for experiment analysis.
    """
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
    
    async def collect_metrics(
        self,
        experiment_name: str,
        variant_name: str,
        duration: str = "1h"
    ) -> ExperimentMetrics:
        """
        Collect metrics for a variant.
        
        Args:
            experiment_name: Experiment name
            variant_name: Variant name
            duration: Time range (e.g., "1h", "24h", "7d")
        
        Returns:
            Aggregated metrics for the variant
        """
        # TODO: Implement actual Prometheus queries
        # This is a placeholder showing the structure
        
        queries = {
            "requests": f'sum(rate(request_latency_seconds_count{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}]))',
            "avg_latency": f'avg(rate(request_latency_seconds_sum{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}]) / rate(request_latency_seconds_count{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}]))',
            "avg_cost": f'avg(rate(llm_cost_dollars_total{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}]))',
            "error_rate": f'sum(rate(http_errors_total{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}])) / sum(rate(request_latency_seconds_count{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}]))',
            "positive_feedback_rate": f'sum(rate(user_feedback_total{{sentiment="positive",experiment="{experiment_name}",variant="{variant_name}"}}[{duration}])) / sum(rate(user_feedback_total{{experiment="{experiment_name}",variant="{variant_name}"}}[{duration}]))',
        }
        
        # Execute queries and aggregate
        metrics = ExperimentMetrics(variant_name=variant_name)
        
        # TODO: Execute queries against Prometheus
        # For now, return placeholder metrics
        return metrics
    
    async def compare_variants(
        self,
        experiment_name: str,
        variant_names: List[str],
        duration: str = "24h"
    ) -> Dict[str, ExperimentMetrics]:
        """
        Compare metrics across variants.
        
        Args:
            experiment_name: Experiment name
            variant_names: List of variant names to compare
            duration: Time range
        
        Returns:
            Dict mapping variant name to metrics
        """
        results = {}
        
        for variant_name in variant_names:
            metrics = await self.collect_metrics(
                experiment_name,
                variant_name,
                duration
            )
            results[variant_name] = metrics
        
        return results


# ============================================================================
# EXPERIMENT EXAMPLES
# ============================================================================

"""
Example 1: Test new embedding model

experiment = Experiment(
    name="embedding_model_v2",
    description="Compare nomic-embed-text v1.5 vs v2.0",
    variants=[
        Variant(
            name="control",
            weight=0.5,
            config={"embedding_model": "nomic-ai/nomic-embed-text-v1.5"}
        ),
        Variant(
            name="treatment",
            weight=0.5,
            config={"embedding_model": "nomic-ai/nomic-embed-text-v2.0"}
        )
    ],
    end_date=datetime.now() + timedelta(days=7)
)

manager = ExperimentManager()
manager.register_experiment(experiment)
experiment.start()

# In RAG retriever:
variant = manager.get_variant("embedding_model_v2", user_id)
if variant:
    embedding_model = variant.config["embedding_model"]
else:
    embedding_model = default_model

# Metrics tracked with experiment label:
track_rag_retrieval(
    agent="specs",
    document_type="manual",
    similarity_scores=[0.89, 0.85],
    search_latency_ms=45.2,
    labels={"experiment": "embedding_model_v2", "variant": variant.name}
)

# After 7 days, compare:
collector = ExperimentMetricsCollector()
results = await collector.compare_variants(
    "embedding_model_v2",
    ["control", "treatment"]
)

# Decision:
if results["treatment"].avg_similarity > results["control"].avg_similarity:
    print("✅ New model performs better!")
    # Roll out to 100%
"""

"""
Example 2: Test confidence threshold

experiment = Experiment(
    name="confidence_threshold",
    description="Test different handoff thresholds",
    variants=[
        Variant(name="control", weight=0.5, config={"threshold": 0.7}),
        Variant(name="treatment", weight=0.5, config={"threshold": 0.6})
    ]
)

# In session manager:
variant = manager.get_variant("confidence_threshold", user_id)
threshold = variant.config["threshold"] if variant else 0.7

if confidence < threshold:
    session.trigger_handoff(
        reason=HandoffReason.LOW_CONFIDENCE,
        confidence_score=confidence,
        labels={"experiment": "confidence_threshold", "variant": variant.name}
    )

# Compare:
# - Handoff rate
# - Task completion rate
# - User satisfaction
"""

"""
Example 3: Test routing algorithm

experiment = Experiment(
    name="routing_algorithm",
    description="LLM classifier vs rule-based",
    variants=[
        Variant(name="llm", weight=0.5, config={"method": "llm"}),
        Variant(name="rules", weight=0.5, config={"method": "rules"})
    ]
)

# In agent router:
variant = manager.get_variant("routing_algorithm", user_id)
if variant and variant.config["method"] == "llm":
    agent, conf = await llm_classifier.classify(message)
else:
    agent, conf = rule_based_classifier.classify(message)

track_agent_routing(
    selected_agent=agent,
    routing_method=variant.config["method"],
    confidence_score=conf,
    labels={"experiment": "routing_algorithm", "variant": variant.name}
)

# Compare:
# - Routing confidence
# - Rerouting rate
# - Task completion
"""
