"""
ML Observability - Model drift detection and monitoring.
"""

import time
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum


class DriftSeverity(Enum):
    """Drift severity level."""
    NORMAL = "normal"
    WARNING = "warning"
    CRITICAL = "critical"


@dataclass
class MetricWindow:
    """Time window for metric aggregation."""
    start: datetime
    end: datetime
    value: float
    count: int
    
    @property
    def duration_hours(self) -> float:
        """Window duration in hours."""
        return (self.end - self.start).total_seconds() / 3600


@dataclass
class DriftDetection:
    """Drift detection result."""
    metric_name: str
    baseline_value: float
    current_value: float
    percent_change: float
    severity: DriftSeverity
    detected_at: datetime
    message: str


class ModelDriftDetector:
    """
    Detects drift in model performance metrics.
    
    Monitors key metrics over time and alerts when significant
    changes are detected compared to baseline.
    """
    
    def __init__(
        self,
        warning_threshold: float = 0.15,  # 15% change
        critical_threshold: float = 0.30  # 30% change
    ):
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.baselines: Dict[str, float] = {}
        self.history: List[DriftDetection] = []
    
    def set_baseline(self, metric_name: str, value: float):
        """
        Set baseline value for a metric.
        
        Args:
            metric_name: Name of metric
            value: Baseline value
        """
        self.baselines[metric_name] = value
    
    def check_drift(
        self,
        metric_name: str,
        current_value: float,
        baseline_value: Optional[float] = None
    ) -> Optional[DriftDetection]:
        """
        Check if current value has drifted from baseline.
        
        Args:
            metric_name: Name of metric
            current_value: Current metric value
            baseline_value: Baseline to compare against (or use stored)
        
        Returns:
            DriftDetection if drift detected, None otherwise
        """
        # Use provided baseline or stored baseline
        if baseline_value is None:
            baseline_value = self.baselines.get(metric_name)
            if baseline_value is None:
                # No baseline set yet - store current as baseline
                self.set_baseline(metric_name, current_value)
                return None
        
        # Calculate percent change
        if baseline_value == 0:
            percent_change = float('inf') if current_value != 0 else 0
        else:
            percent_change = abs((current_value - baseline_value) / baseline_value)
        
        # Determine severity
        if percent_change >= self.critical_threshold:
            severity = DriftSeverity.CRITICAL
        elif percent_change >= self.warning_threshold:
            severity = DriftSeverity.WARNING
        else:
            severity = DriftSeverity.NORMAL
        
        # Only return detection if drift is significant
        if severity == DriftSeverity.NORMAL:
            return None
        
        # Create detection
        detection = DriftDetection(
            metric_name=metric_name,
            baseline_value=baseline_value,
            current_value=current_value,
            percent_change=percent_change * 100,  # Convert to percentage
            severity=severity,
            detected_at=datetime.now(),
            message=self._format_message(
                metric_name,
                baseline_value,
                current_value,
                percent_change * 100
            )
        )
        
        # Store in history
        self.history.append(detection)
        
        return detection
    
    def _format_message(
        self,
        metric_name: str,
        baseline: float,
        current: float,
        percent_change: float
    ) -> str:
        """Format human-readable drift message."""
        direction = "increased" if current > baseline else "decreased"
        return (
            f"{metric_name} has {direction} by {percent_change:.1f}% "
            f"(baseline: {baseline:.3f}, current: {current:.3f})"
        )
    
    def get_recent_drifts(
        self,
        hours: int = 24,
        min_severity: DriftSeverity = DriftSeverity.WARNING
    ) -> List[DriftDetection]:
        """
        Get recent drift detections.
        
        Args:
            hours: Look back this many hours
            min_severity: Minimum severity to include
        
        Returns:
            List of recent drift detections
        """
        cutoff = datetime.now() - timedelta(hours=hours)
        severity_order = [DriftSeverity.NORMAL, DriftSeverity.WARNING, DriftSeverity.CRITICAL]
        min_severity_index = severity_order.index(min_severity)
        
        return [
            d for d in self.history
            if d.detected_at >= cutoff
            and severity_order.index(d.severity) >= min_severity_index
        ]


class PerformanceMonitor:
    """
    Monitors model performance metrics for drift.
    
    Tracks key metrics and compares rolling windows to detect
    degradation or improvement.
    """
    
    MONITORED_METRICS = {
        # Metric name: (direction, description)
        "avg_similarity": ("decrease", "RAG retrieval quality"),
        "cache_hit_rate": ("decrease", "Cache efficiency"),
        "completion_rate": ("decrease", "Task success rate"),
        "routing_confidence": ("decrease", "Routing quality"),
        "avg_latency": ("increase", "Response speed"),
        "error_rate": ("increase", "System reliability"),
        "handoff_rate": ("increase", "Human escalation"),
        "avg_cost": ("increase", "LLM spend"),
    }
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
        self.drift_detector = ModelDriftDetector(
            warning_threshold=0.15,  # 15%
            critical_threshold=0.30  # 30%
        )
    
    async def collect_baseline(self, lookback_days: int = 7):
        """
        Collect baseline metrics over lookback period.
        
        Args:
            lookback_days: Days to average for baseline
        """
        # TODO: Implement Prometheus queries
        # For now, use placeholder values
        baselines = {
            "avg_similarity": 0.82,
            "cache_hit_rate": 0.65,
            "completion_rate": 0.75,
            "routing_confidence": 0.85,
            "avg_latency": 1.5,
            "error_rate": 0.02,
            "handoff_rate": 0.10,
            "avg_cost": 0.05,
        }
        
        for metric, value in baselines.items():
            self.drift_detector.set_baseline(metric, value)
    
    async def check_drift(self) -> List[DriftDetection]:
        """
        Check all metrics for drift.
        
        Returns:
            List of detected drifts
        """
        # TODO: Query current metrics from Prometheus
        # For now, use placeholder values
        current_metrics = {
            "avg_similarity": 0.70,  # -15% drift (warning)
            "cache_hit_rate": 0.63,  # Normal
            "completion_rate": 0.52,  # -31% drift (critical)
            "routing_confidence": 0.84,  # Normal
            "avg_latency": 2.1,  # +40% drift (critical)
            "error_rate": 0.024,  # Normal
            "handoff_rate": 0.12,  # Normal
            "avg_cost": 0.07,  # +40% drift (critical)
        }
        
        drifts = []
        
        for metric_name, current_value in current_metrics.items():
            drift = self.drift_detector.check_drift(metric_name, current_value)
            if drift:
                drifts.append(drift)
        
        return drifts
    
    def generate_report(self, drifts: List[DriftDetection]) -> str:
        """
        Generate human-readable drift report.
        
        Args:
            drifts: List of drift detections
        
        Returns:
            Formatted report string
        """
        if not drifts:
            return "✅ No significant drift detected. All metrics within normal range."
        
        # Group by severity
        critical = [d for d in drifts if d.severity == DriftSeverity.CRITICAL]
        warning = [d for d in drifts if d.severity == DriftSeverity.WARNING]
        
        lines = ["# Model Drift Report", ""]
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")
        
        if critical:
            lines.append("## 🔴 CRITICAL Drifts")
            lines.append("")
            for d in critical:
                lines.append(f"- **{d.metric_name}**: {d.message}")
            lines.append("")
        
        if warning:
            lines.append("## ⚠️ WARNING Drifts")
            lines.append("")
            for d in warning:
                lines.append(f"- **{d.metric_name}**: {d.message}")
            lines.append("")
        
        lines.append("## Recommendations")
        lines.append("")
        
        if critical:
            lines.append("**Immediate action required:**")
            for d in critical:
                direction, desc = self.MONITORED_METRICS.get(d.metric_name, ("", ""))
                if direction == "decrease" and d.current_value < d.baseline_value:
                    lines.append(f"- Investigate {d.metric_name} degradation ({desc})")
                elif direction == "increase" and d.current_value > d.baseline_value:
                    lines.append(f"- Investigate {d.metric_name} spike ({desc})")
        
        if warning:
            lines.append("**Monitor closely:**")
            for d in warning:
                lines.append(f"- Watch {d.metric_name} trend")
        
        return "\n".join(lines)


# ============================================================================
# PROMETHEUS INTEGRATION
# ============================================================================

class PrometheusMetricsCollector:
    """
    Collects metrics from Prometheus for drift detection.
    """
    
    def __init__(self, prometheus_url: str = "http://localhost:9090"):
        self.prometheus_url = prometheus_url
    
    async def query_metric(
        self,
        query: str,
        time_range: str = "1h"
    ) -> float:
        """
        Execute Prometheus query and return single value.
        
        Args:
            query: PromQL query
            time_range: Time range for query
        
        Returns:
            Metric value
        """
        # TODO: Implement actual Prometheus API call
        # For now, return placeholder
        return 0.0
    
    async def collect_metric_window(
        self,
        metric_name: str,
        window_hours: int = 1
    ) -> MetricWindow:
        """
        Collect metric over time window.
        
        Args:
            metric_name: Name of metric to collect
            window_hours: Window size in hours
        
        Returns:
            Aggregated metric window
        """
        # Map metric name to Prometheus query
        queries = {
            "avg_similarity": "avg(rag_similarity_score)",
            "cache_hit_rate": 'rate(cache_operations_total{operation="hit"}[1h]) / rate(cache_operations_total[1h])',
            "completion_rate": 'rate(task_completion_total{status="completed"}[1h]) / rate(task_completion_total[1h])',
            "routing_confidence": "avg(agent_routing_confidence)",
            "avg_latency": 'avg(rate(request_latency_seconds_sum[1h]) / rate(request_latency_seconds_count[1h]))',
            "error_rate": 'rate(http_errors_total[1h]) / rate(request_latency_seconds_count[1h])',
            "handoff_rate": 'rate(human_handoff_total[1h]) / rate(request_latency_seconds_count[1h])',
            "avg_cost": 'rate(llm_cost_dollars_total[1h])',
        }
        
        query = queries.get(metric_name)
        if not query:
            raise ValueError(f"Unknown metric: {metric_name}")
        
        # Execute query
        value = await self.query_metric(query, f"{window_hours}h")
        
        end = datetime.now()
        start = end - timedelta(hours=window_hours)
        
        return MetricWindow(
            start=start,
            end=end,
            value=value,
            count=1  # Placeholder
        )


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
from observability.model_drift import PerformanceMonitor, ModelDriftDetector

# Initialize monitor
monitor = PerformanceMonitor()

# Collect baseline (run once, then periodically)
await monitor.collect_baseline(lookback_days=7)

# Check for drift (run hourly/daily)
drifts = await monitor.check_drift()

if drifts:
    # Generate report
    report = monitor.generate_report(drifts)
    print(report)
    
    # Send alert
    await send_slack_alert(report)
    
    # Log to file
    with open(f"drift-report-{datetime.now():%Y%m%d}.md", "w") as f:
        f.write(report)

# View drift history
recent_drifts = monitor.drift_detector.get_recent_drifts(hours=24)
for drift in recent_drifts:
    print(f"{drift.severity.value}: {drift.message}")

# Manual drift check
detector = ModelDriftDetector(warning_threshold=0.10, critical_threshold=0.25)
detector.set_baseline("user_satisfaction", 0.80)

# Later...
drift = detector.check_drift("user_satisfaction", 0.65)
if drift:
    print(drift.message)
    # Output: "user_satisfaction has decreased by 18.8% (baseline: 0.800, current: 0.650)"
"""
