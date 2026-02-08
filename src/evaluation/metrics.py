"""RAG quality metrics for evaluation."""

import time
import math
from typing import List, Optional
from dataclasses import dataclass, field
from datetime import datetime

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


@dataclass
class RetrievalMetrics:
    """Metrics for retrieval quality."""
    
    precision_at_k: float = 0.0  # Relevant docs in top K / K
    recall_at_k: float = 0.0     # Relevant docs in top K / Total relevant
    mrr: float = 0.0             # Mean Reciprocal Rank
    ndcg: float = 0.0            # Normalized Discounted Cumulative Gain
    hit_rate: float = 0.0        # Queries with at least 1 relevant doc
    avg_score: float = 0.0       # Average similarity score
    
    def to_dict(self) -> dict:
        return {
            "precision_at_k": round(self.precision_at_k, 4),
            "recall_at_k": round(self.recall_at_k, 4),
            "mrr": round(self.mrr, 4),
            "ndcg": round(self.ndcg, 4),
            "hit_rate": round(self.hit_rate, 4),
            "avg_score": round(self.avg_score, 4),
        }


@dataclass
class GenerationMetrics:
    """Metrics for generation quality."""
    
    faithfulness: float = 0.0      # Is answer grounded in context?
    answer_relevance: float = 0.0  # Does answer address the question?
    context_relevance: float = 0.0 # Is retrieved context relevant?
    completeness: float = 0.0      # Does answer fully address query?
    
    def to_dict(self) -> dict:
        return {
            "faithfulness": round(self.faithfulness, 4),
            "answer_relevance": round(self.answer_relevance, 4),
            "context_relevance": round(self.context_relevance, 4),
            "completeness": round(self.completeness, 4),
        }


@dataclass
class LatencyMetrics:
    """Metrics for system latency."""
    
    retrieval_ms: float = 0.0
    generation_ms: float = 0.0
    total_ms: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "retrieval_ms": round(self.retrieval_ms, 2),
            "generation_ms": round(self.generation_ms, 2),
            "total_ms": round(self.total_ms, 2),
        }


@dataclass
class EvaluationResult:
    """Complete evaluation result for a single query."""
    
    query: str
    expected_answer: Optional[str] = None
    generated_answer: Optional[str] = None
    retrieved_contexts: List[str] = field(default_factory=list)
    retrieval_scores: List[float] = field(default_factory=list)
    retrieval_metrics: RetrievalMetrics = field(default_factory=RetrievalMetrics)
    generation_metrics: GenerationMetrics = field(default_factory=GenerationMetrics)
    latency_metrics: LatencyMetrics = field(default_factory=LatencyMetrics)
    tokens_used: int = 0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> dict:
        return {
            "query": self.query,
            "expected_answer": self.expected_answer,
            "generated_answer": self.generated_answer,
            "retrieved_contexts_count": len(self.retrieved_contexts),
            "retrieval_metrics": self.retrieval_metrics.to_dict(),
            "generation_metrics": self.generation_metrics.to_dict(),
            "latency_metrics": self.latency_metrics.to_dict(),
            "tokens_used": self.tokens_used,
            "timestamp": self.timestamp,
        }
    
    @property
    def overall_score(self) -> float:
        """Calculate overall quality score (0-1)."""
        weights = {
            "faithfulness": 0.25,
            "answer_relevance": 0.25,
            "context_relevance": 0.20,
            "retrieval": 0.30,
        }
        
        retrieval_score = (
            self.retrieval_metrics.precision_at_k * 0.4 +
            self.retrieval_metrics.mrr * 0.3 +
            self.retrieval_metrics.hit_rate * 0.3
        )
        
        return (
            self.generation_metrics.faithfulness * weights["faithfulness"] +
            self.generation_metrics.answer_relevance * weights["answer_relevance"] +
            self.generation_metrics.context_relevance * weights["context_relevance"] +
            retrieval_score * weights["retrieval"]
        )


class MetricsCalculator:
    """Calculate retrieval and generation metrics."""
    
    @staticmethod
    def precision_at_k(relevant_items: List[bool], k: int = None) -> float:
        """Calculate Precision@K."""
        if not relevant_items:
            return 0.0
        k = k or len(relevant_items)
        relevant_in_k = sum(relevant_items[:k])
        return relevant_in_k / k
    
    @staticmethod
    def recall_at_k(relevant_items: List[bool], total_relevant: int, k: int = None) -> float:
        """Calculate Recall@K."""
        if total_relevant == 0:
            return 0.0
        k = k or len(relevant_items)
        relevant_in_k = sum(relevant_items[:k])
        return relevant_in_k / total_relevant
    
    @staticmethod
    def mrr(relevant_items: List[bool]) -> float:
        """Calculate Mean Reciprocal Rank."""
        for i, is_relevant in enumerate(relevant_items):
            if is_relevant:
                return 1.0 / (i + 1)
        return 0.0
    
    @staticmethod
    def ndcg(relevance_scores: List[float], k: int = None) -> float:
        """Calculate Normalized Discounted Cumulative Gain."""
        if not relevance_scores:
            return 0.0
        
        k = k or len(relevance_scores)
        scores = relevance_scores[:k]
        
        # DCG
        dcg = sum(
            score / math.log2(i + 2)
            for i, score in enumerate(scores)
        )
        
        # Ideal DCG (sorted scores)
        ideal_scores = sorted(scores, reverse=True)
        idcg = sum(
            score / math.log2(i + 2)
            for i, score in enumerate(ideal_scores)
        )
        
        return dcg / idcg if idcg > 0 else 0.0
    
    @staticmethod
    def hit_rate(relevant_items: List[bool]) -> float:
        """Calculate if at least one relevant item was retrieved."""
        return 1.0 if any(relevant_items) else 0.0


class LLMJudge:
    """Use LLM to evaluate generation quality."""
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.0,
            default_headers={
                "HTTP-Referer": "https://github.com/genai-auto",
                "X-Title": "GenAI Auto - RAG Evaluator",
            },
        )
    
    async def evaluate_faithfulness(
        self,
        answer: str,
        contexts: List[str],
    ) -> float:
        """Evaluate if the answer is grounded in the provided contexts."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an evaluation judge. Your task is to evaluate if an answer is faithful to the given contexts.

Faithfulness means the answer only contains information that can be derived from the contexts.

Score from 0 to 1:
- 1.0: Completely faithful, all claims are supported by contexts
- 0.5: Partially faithful, some claims are not supported
- 0.0: Not faithful, contains hallucinated information

Respond with ONLY a number between 0 and 1."""),
            ("human", """Contexts:
{contexts}

Answer:
{answer}

Faithfulness score (0-1):"""),
        ])
        
        response = await (prompt | self.llm).ainvoke({
            "contexts": "\n---\n".join(contexts),
            "answer": answer,
        })
        
        try:
            return float(response.content.strip())
        except ValueError:
            return 0.5
    
    async def evaluate_answer_relevance(
        self,
        query: str,
        answer: str,
    ) -> float:
        """Evaluate if the answer addresses the question."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an evaluation judge. Your task is to evaluate if an answer is relevant to the question.

Answer relevance means the answer directly addresses what was asked.

Score from 0 to 1:
- 1.0: Highly relevant, directly and completely answers the question
- 0.5: Partially relevant, addresses some aspects
- 0.0: Not relevant, does not answer the question

Respond with ONLY a number between 0 and 1."""),
            ("human", """Question:
{query}

Answer:
{answer}

Answer relevance score (0-1):"""),
        ])
        
        response = await (prompt | self.llm).ainvoke({
            "query": query,
            "answer": answer,
        })
        
        try:
            return float(response.content.strip())
        except ValueError:
            return 0.5
    
    async def evaluate_context_relevance(
        self,
        query: str,
        contexts: List[str],
    ) -> float:
        """Evaluate if the retrieved contexts are relevant to the query."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an evaluation judge. Your task is to evaluate if retrieved contexts are relevant to a query.

Context relevance means the contexts contain information useful for answering the query.

Score from 0 to 1:
- 1.0: Highly relevant, contexts contain all needed information
- 0.5: Partially relevant, some useful information
- 0.0: Not relevant, contexts don't help answer the query

Respond with ONLY a number between 0 and 1."""),
            ("human", """Query:
{query}

Retrieved Contexts:
{contexts}

Context relevance score (0-1):"""),
        ])
        
        response = await (prompt | self.llm).ainvoke({
            "query": query,
            "contexts": "\n---\n".join(contexts),
        })
        
        try:
            return float(response.content.strip())
        except ValueError:
            return 0.5
    
    async def evaluate_completeness(
        self,
        query: str,
        answer: str,
        expected_answer: str = None,
    ) -> float:
        """Evaluate if the answer fully addresses the query."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", """You are an evaluation judge. Your task is to evaluate if an answer is complete.

Completeness means the answer fully addresses all aspects of the question.

{expected_context}

Score from 0 to 1:
- 1.0: Complete, addresses all aspects of the question
- 0.5: Partial, misses some aspects
- 0.0: Incomplete, major aspects missing

Respond with ONLY a number between 0 and 1."""),
            ("human", """Question:
{query}

Answer:
{answer}

Completeness score (0-1):"""),
        ])
        
        expected_context = ""
        if expected_answer:
            expected_context = f"Expected answer for reference: {expected_answer}"
        
        response = await (prompt | self.llm).ainvoke({
            "query": query,
            "answer": answer,
            "expected_context": expected_context,
        })
        
        try:
            return float(response.content.strip())
        except ValueError:
            return 0.5


class RAGEvaluator:
    """Main RAG evaluation orchestrator."""
    
    def __init__(self, db_session=None):
        self.db = db_session
        self.calculator = MetricsCalculator()
        self.judge = LLMJudge()
    
    async def evaluate_retrieval(
        self,
        query: str,
        retrieved_docs: List[dict],
        relevant_doc_ids: List[str] = None,
        k: int = 5,
    ) -> RetrievalMetrics:
        """Evaluate retrieval quality."""
        scores = [doc.get("score", 0) for doc in retrieved_docs[:k]]
        
        # If we have ground truth relevance
        if relevant_doc_ids:
            doc_ids = [doc.get("document_id", doc.get("id", "")) for doc in retrieved_docs]
            relevant_items = [doc_id in relevant_doc_ids for doc_id in doc_ids[:k]]
            
            return RetrievalMetrics(
                precision_at_k=self.calculator.precision_at_k(relevant_items, k),
                recall_at_k=self.calculator.recall_at_k(relevant_items, len(relevant_doc_ids), k),
                mrr=self.calculator.mrr(relevant_items),
                ndcg=self.calculator.ndcg(scores, k),
                hit_rate=self.calculator.hit_rate(relevant_items),
                avg_score=sum(scores) / len(scores) if scores else 0,
            )
        
        # Without ground truth, use scores as proxy
        return RetrievalMetrics(
            precision_at_k=sum(1 for s in scores if s > 0.7) / k if scores else 0,
            recall_at_k=0.0,  # Can't calculate without ground truth
            mrr=1.0 if scores and scores[0] > 0.7 else 0.0,
            ndcg=self.calculator.ndcg(scores, k),
            hit_rate=1.0 if any(s > 0.7 for s in scores) else 0.0,
            avg_score=sum(scores) / len(scores) if scores else 0,
        )
    
    async def evaluate_generation(
        self,
        query: str,
        answer: str,
        contexts: List[str],
        expected_answer: str = None,
    ) -> GenerationMetrics:
        """Evaluate generation quality using LLM judge."""
        faithfulness = await self.judge.evaluate_faithfulness(answer, contexts)
        answer_relevance = await self.judge.evaluate_answer_relevance(query, answer)
        context_relevance = await self.judge.evaluate_context_relevance(query, contexts)
        completeness = await self.judge.evaluate_completeness(query, answer, expected_answer)
        
        return GenerationMetrics(
            faithfulness=faithfulness,
            answer_relevance=answer_relevance,
            context_relevance=context_relevance,
            completeness=completeness,
        )
    
    async def evaluate_single(
        self,
        query: str,
        expected_answer: str = None,
        relevant_doc_ids: List[str] = None,
        k: int = 5,
    ) -> EvaluationResult:
        """Run full evaluation on a single query."""
        from src.rag.pipeline import RAGPipeline
        from src.storage.database import async_session
        
        result = EvaluationResult(
            query=query,
            expected_answer=expected_answer,
        )
        
        async with async_session() as db:
            pipeline = RAGPipeline(db)
            
            # Measure retrieval
            retrieval_start = time.perf_counter()
            search_results = await pipeline.query(query, top_k=k)
            retrieval_time = (time.perf_counter() - retrieval_start) * 1000
            
            result.retrieved_contexts = [r.content for r in search_results]
            result.retrieval_scores = [r.score for r in search_results]
            
            # Evaluate retrieval
            result.retrieval_metrics = await self.evaluate_retrieval(
                query,
                [r.to_dict() for r in search_results],
                relevant_doc_ids,
                k,
            )
            
            # Generate answer
            generation_start = time.perf_counter()
            _context = await pipeline.get_context(query, top_k=k)
            
            from src.agents.specs.agent import SpecsAgent
            agent = SpecsAgent()
            state = {
                "messages": [{"role": "user", "content": query}],
                "session_id": "eval-session",
                "customer_id": None,
                "vehicle_id": None,
                "metadata": {},
                "current_agent": "specs",
                "context": {},
            }
            result.generated_answer = await agent.process(state)
            generation_time = (time.perf_counter() - generation_start) * 1000
            
            # Evaluate generation
            result.generation_metrics = await self.evaluate_generation(
                query,
                result.generated_answer,
                result.retrieved_contexts,
                expected_answer,
            )
            
            # Latency metrics
            result.latency_metrics = LatencyMetrics(
                retrieval_ms=retrieval_time,
                generation_ms=generation_time,
                total_ms=retrieval_time + generation_time,
            )
        
        return result
