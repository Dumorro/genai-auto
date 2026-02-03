"""Evaluation runner for batch evaluation and reporting."""

import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field, asdict
from pathlib import Path

import structlog

from src.evaluation.metrics import RAGEvaluator, EvaluationResult
from src.evaluation.dataset import EvaluationDataset, TestCase

logger = structlog.get_logger()


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    
    name: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    dataset_name: str = ""
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    
    # Aggregate metrics
    avg_retrieval_precision: float = 0.0
    avg_retrieval_mrr: float = 0.0
    avg_retrieval_hit_rate: float = 0.0
    avg_faithfulness: float = 0.0
    avg_answer_relevance: float = 0.0
    avg_context_relevance: float = 0.0
    avg_completeness: float = 0.0
    avg_overall_score: float = 0.0
    
    # Latency
    avg_retrieval_latency_ms: float = 0.0
    avg_generation_latency_ms: float = 0.0
    avg_total_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    
    # Per-category breakdown
    category_scores: Dict[str, float] = field(default_factory=dict)
    
    # Individual results
    results: List[dict] = field(default_factory=list)
    errors: List[dict] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent)
    
    def save(self, path: str):
        """Save report to JSON file."""
        with open(path, 'w') as f:
            f.write(self.to_json())
        logger.info("Report saved", path=path)
    
    def summary(self) -> str:
        """Generate a text summary of the report."""
        return f"""
╔══════════════════════════════════════════════════════════════╗
║                    RAG EVALUATION REPORT                      ║
╠══════════════════════════════════════════════════════════════╣
║ Name: {self.name:<54} ║
║ Dataset: {self.dataset_name:<51} ║
║ Timestamp: {self.timestamp:<49} ║
╠══════════════════════════════════════════════════════════════╣
║ QUERIES                                                       ║
║   Total: {self.total_queries:<52} ║
║   Successful: {self.successful_queries:<47} ║
║   Failed: {self.failed_queries:<51} ║
╠══════════════════════════════════════════════════════════════╣
║ RETRIEVAL METRICS                                             ║
║   Precision@K: {self.avg_retrieval_precision:<45.4f} ║
║   MRR: {self.avg_retrieval_mrr:<54.4f} ║
║   Hit Rate: {self.avg_retrieval_hit_rate:<49.4f} ║
╠══════════════════════════════════════════════════════════════╣
║ GENERATION METRICS                                            ║
║   Faithfulness: {self.avg_faithfulness:<44.4f} ║
║   Answer Relevance: {self.avg_answer_relevance:<40.4f} ║
║   Context Relevance: {self.avg_context_relevance:<39.4f} ║
║   Completeness: {self.avg_completeness:<45.4f} ║
╠══════════════════════════════════════════════════════════════╣
║ OVERALL SCORE: {self.avg_overall_score:<45.4f} ║
╠══════════════════════════════════════════════════════════════╣
║ LATENCY                                                       ║
║   Avg Retrieval: {self.avg_retrieval_latency_ms:<43.2f} ms ║
║   Avg Generation: {self.avg_generation_latency_ms:<42.2f} ms ║
║   Avg Total: {self.avg_total_latency_ms:<48.2f} ms ║
║   P95: {self.p95_latency_ms:<54.2f} ms ║
╠══════════════════════════════════════════════════════════════╣
║ CATEGORY BREAKDOWN                                            ║
{self._format_categories()}╚══════════════════════════════════════════════════════════════╝
"""
    
    def _format_categories(self) -> str:
        lines = []
        for category, score in sorted(self.category_scores.items()):
            lines.append(f"║   {category:<20}: {score:<38.4f} ║\n")
        return "".join(lines) if lines else "║   No categories                                              ║\n"


class EvaluationRunner:
    """Run evaluations on test datasets."""
    
    def __init__(self):
        self.evaluator = RAGEvaluator()
    
    async def run_single(
        self,
        test_case: TestCase,
        k: int = 5,
    ) -> EvaluationResult:
        """Run evaluation on a single test case."""
        logger.info("Evaluating test case", id=test_case.id, query=test_case.query[:50])
        
        return await self.evaluator.evaluate_single(
            query=test_case.query,
            expected_answer=test_case.expected_answer,
            relevant_doc_ids=test_case.relevant_doc_ids,
            k=k,
        )
    
    async def run_dataset(
        self,
        dataset: EvaluationDataset,
        name: str = "evaluation",
        k: int = 5,
        max_concurrent: int = 3,
        categories: List[str] = None,
        difficulties: List[str] = None,
    ) -> EvaluationReport:
        """Run evaluation on an entire dataset."""
        report = EvaluationReport(
            name=name,
            dataset_name=dataset.name,
        )
        
        # Filter test cases
        test_cases = list(dataset)
        
        if categories:
            test_cases = [tc for tc in test_cases if tc.category in categories]
        
        if difficulties:
            test_cases = [tc for tc in test_cases if tc.difficulty in difficulties]
        
        report.total_queries = len(test_cases)
        logger.info(
            "Starting evaluation",
            name=name,
            total_cases=len(test_cases),
        )
        
        # Run evaluations with concurrency limit
        semaphore = asyncio.Semaphore(max_concurrent)
        results: List[EvaluationResult] = []
        errors: List[dict] = []
        
        async def evaluate_with_limit(test_case: TestCase):
            async with semaphore:
                try:
                    result = await self.run_single(test_case, k)
                    return ("success", test_case, result)
                except Exception as e:
                    logger.error("Evaluation failed", id=test_case.id, error=str(e))
                    return ("error", test_case, str(e))
        
        tasks = [evaluate_with_limit(tc) for tc in test_cases]
        completed = await asyncio.gather(*tasks)
        
        # Process results
        category_results: Dict[str, List[float]] = {}
        latencies: List[float] = []
        
        for status, test_case, data in completed:
            if status == "success":
                result: EvaluationResult = data
                results.append(result)
                report.results.append(result.to_dict())
                report.successful_queries += 1
                latencies.append(result.latency_metrics.total_ms)
                
                # Category tracking
                if test_case.category not in category_results:
                    category_results[test_case.category] = []
                category_results[test_case.category].append(result.overall_score)
            else:
                report.failed_queries += 1
                errors.append({
                    "test_case_id": test_case.id,
                    "query": test_case.query,
                    "error": data,
                })
        
        report.errors = errors
        
        # Calculate aggregate metrics
        if results:
            n = len(results)
            
            report.avg_retrieval_precision = sum(r.retrieval_metrics.precision_at_k for r in results) / n
            report.avg_retrieval_mrr = sum(r.retrieval_metrics.mrr for r in results) / n
            report.avg_retrieval_hit_rate = sum(r.retrieval_metrics.hit_rate for r in results) / n
            
            report.avg_faithfulness = sum(r.generation_metrics.faithfulness for r in results) / n
            report.avg_answer_relevance = sum(r.generation_metrics.answer_relevance for r in results) / n
            report.avg_context_relevance = sum(r.generation_metrics.context_relevance for r in results) / n
            report.avg_completeness = sum(r.generation_metrics.completeness for r in results) / n
            
            report.avg_overall_score = sum(r.overall_score for r in results) / n
            
            report.avg_retrieval_latency_ms = sum(r.latency_metrics.retrieval_ms for r in results) / n
            report.avg_generation_latency_ms = sum(r.latency_metrics.generation_ms for r in results) / n
            report.avg_total_latency_ms = sum(r.latency_metrics.total_ms for r in results) / n
            
            if latencies:
                sorted_latencies = sorted(latencies)
                p95_idx = int(len(sorted_latencies) * 0.95)
                report.p95_latency_ms = sorted_latencies[min(p95_idx, len(sorted_latencies) - 1)]
            
            # Category scores
            for category, scores in category_results.items():
                report.category_scores[category] = sum(scores) / len(scores)
        
        logger.info(
            "Evaluation complete",
            name=name,
            successful=report.successful_queries,
            failed=report.failed_queries,
            overall_score=report.avg_overall_score,
        )
        
        return report
    
    async def compare_runs(
        self,
        reports: List[EvaluationReport],
    ) -> dict:
        """Compare multiple evaluation runs."""
        if len(reports) < 2:
            return {"error": "Need at least 2 reports to compare"}
        
        comparison = {
            "runs": [r.name for r in reports],
            "metrics": {},
        }
        
        metrics = [
            "avg_retrieval_precision",
            "avg_retrieval_mrr",
            "avg_faithfulness",
            "avg_answer_relevance",
            "avg_overall_score",
            "avg_total_latency_ms",
        ]
        
        for metric in metrics:
            values = [getattr(r, metric) for r in reports]
            comparison["metrics"][metric] = {
                "values": values,
                "best": max(values) if "latency" not in metric else min(values),
                "improvement": ((values[-1] - values[0]) / values[0] * 100) if values[0] != 0 else 0,
            }
        
        return comparison
