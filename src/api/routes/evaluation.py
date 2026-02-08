"""Evaluation API endpoints."""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_db
from src.api.auth import get_current_user, AuthenticatedUser
from src.evaluation.metrics import RAGEvaluator
from src.evaluation.dataset import create_sample_dataset, EvaluationDataset, TestCase
from src.evaluation.runner import EvaluationRunner

logger = structlog.get_logger()
router = APIRouter()

# Store running evaluations
_running_evaluations = {}
_evaluation_results = {}


# ============== Request/Response Models ==============

class SingleEvalRequest(BaseModel):
    """Request to evaluate a single query."""
    
    query: str = Field(..., description="Query to evaluate")
    expected_answer: Optional[str] = Field(None, description="Expected answer for comparison")
    k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")


class SingleEvalResponse(BaseModel):
    """Response for single query evaluation."""
    
    query: str
    generated_answer: str
    retrieval_metrics: dict
    generation_metrics: dict
    latency_metrics: dict
    overall_score: float


class BatchEvalRequest(BaseModel):
    """Request to run batch evaluation."""
    
    name: str = Field(..., description="Evaluation run name")
    use_sample_dataset: bool = Field(default=True, description="Use built-in sample dataset")
    categories: Optional[List[str]] = Field(None, description="Filter by categories")
    difficulties: Optional[List[str]] = Field(None, description="Filter by difficulties")
    k: int = Field(default=5, ge=1, le=20, description="Number of documents to retrieve")
    max_concurrent: int = Field(default=3, ge=1, le=10, description="Max concurrent evaluations")


class BatchEvalStatus(BaseModel):
    """Status of a batch evaluation."""
    
    name: str
    status: str  # pending, running, completed, failed
    progress: int = 0
    total: int = 0
    message: str = ""


class TestCaseInput(BaseModel):
    """Input for a custom test case."""
    
    id: str
    query: str
    expected_answer: Optional[str] = None
    category: str = "general"
    difficulty: str = "medium"


class CustomDatasetRequest(BaseModel):
    """Request to run evaluation with custom test cases."""
    
    name: str
    test_cases: List[TestCaseInput]
    k: int = Field(default=5, ge=1, le=20)


# ============== Endpoints ==============

@router.post("/evaluation/single", response_model=SingleEvalResponse)
async def evaluate_single_query(
    request: SingleEvalRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Evaluate a single query and get quality metrics."""
    logger.info(
        "Single query evaluation",
        query=request.query[:50],
        user=user.email,
    )
    
    try:
        evaluator = RAGEvaluator(db)
        result = await evaluator.evaluate_single(
            query=request.query,
            expected_answer=request.expected_answer,
            k=request.k,
        )
        
        return SingleEvalResponse(
            query=result.query,
            generated_answer=result.generated_answer or "",
            retrieval_metrics=result.retrieval_metrics.to_dict(),
            generation_metrics=result.generation_metrics.to_dict(),
            latency_metrics=result.latency_metrics.to_dict(),
            overall_score=result.overall_score,
        )
    
    except Exception as e:
        logger.error("Single evaluation failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/evaluation/batch")
async def start_batch_evaluation(
    request: BatchEvalRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Start a batch evaluation (runs in background)."""
    if request.name in _running_evaluations:
        raise HTTPException(
            status_code=400,
            detail=f"Evaluation '{request.name}' is already running",
        )
    
    logger.info(
        "Starting batch evaluation",
        name=request.name,
        user=user.email,
    )
    
    # Create dataset
    if request.use_sample_dataset:
        dataset = create_sample_dataset()
    else:
        raise HTTPException(
            status_code=400,
            detail="Custom dataset not provided. Use /evaluation/custom endpoint.",
        )
    
    # Initialize status
    _running_evaluations[request.name] = {
        "status": "pending",
        "progress": 0,
        "total": len(dataset),
        "message": "Starting evaluation...",
    }
    
    # Run in background
    async def run_evaluation():
        try:
            _running_evaluations[request.name]["status"] = "running"
            
            runner = EvaluationRunner()
            report = await runner.run_dataset(
                dataset=dataset,
                name=request.name,
                k=request.k,
                max_concurrent=request.max_concurrent,
                categories=request.categories,
                difficulties=request.difficulties,
            )
            
            _evaluation_results[request.name] = report
            _running_evaluations[request.name] = {
                "status": "completed",
                "progress": len(dataset),
                "total": len(dataset),
                "message": f"Completed with overall score: {report.avg_overall_score:.4f}",
            }
            
        except Exception as e:
            logger.error("Batch evaluation failed", name=request.name, error=str(e))
            _running_evaluations[request.name] = {
                "status": "failed",
                "progress": 0,
                "total": len(dataset),
                "message": str(e),
            }
    
    background_tasks.add_task(run_evaluation)
    
    return {
        "message": f"Evaluation '{request.name}' started",
        "status_endpoint": f"/api/v1/evaluation/status/{request.name}",
    }


@router.post("/evaluation/custom")
async def run_custom_evaluation(
    request: CustomDatasetRequest,
    background_tasks: BackgroundTasks,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Run evaluation with custom test cases."""
    if request.name in _running_evaluations:
        raise HTTPException(
            status_code=400,
            detail=f"Evaluation '{request.name}' is already running",
        )
    
    # Create dataset from custom test cases
    dataset = EvaluationDataset(name=f"custom-{request.name}")
    for tc in request.test_cases:
        dataset.add_test_case(TestCase(
            id=tc.id,
            query=tc.query,
            expected_answer=tc.expected_answer,
            category=tc.category,
            difficulty=tc.difficulty,
        ))
    
    logger.info(
        "Starting custom evaluation",
        name=request.name,
        test_cases=len(dataset),
    )
    
    _running_evaluations[request.name] = {
        "status": "pending",
        "progress": 0,
        "total": len(dataset),
        "message": "Starting evaluation...",
    }
    
    async def run_evaluation():
        try:
            _running_evaluations[request.name]["status"] = "running"
            
            runner = EvaluationRunner()
            report = await runner.run_dataset(
                dataset=dataset,
                name=request.name,
                k=request.k,
            )
            
            _evaluation_results[request.name] = report
            _running_evaluations[request.name] = {
                "status": "completed",
                "progress": len(dataset),
                "total": len(dataset),
                "message": f"Completed with overall score: {report.avg_overall_score:.4f}",
            }
            
        except Exception as e:
            _running_evaluations[request.name] = {
                "status": "failed",
                "message": str(e),
            }
    
    background_tasks.add_task(run_evaluation)
    
    return {
        "message": f"Custom evaluation '{request.name}' started",
        "test_cases": len(dataset),
    }


@router.get("/evaluation/status/{name}", response_model=BatchEvalStatus)
async def get_evaluation_status(
    name: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get status of a running or completed evaluation."""
    if name not in _running_evaluations:
        raise HTTPException(status_code=404, detail=f"Evaluation '{name}' not found")
    
    status = _running_evaluations[name]
    return BatchEvalStatus(
        name=name,
        status=status["status"],
        progress=status.get("progress", 0),
        total=status.get("total", 0),
        message=status.get("message", ""),
    )


@router.get("/evaluation/results/{name}")
async def get_evaluation_results(
    name: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get results of a completed evaluation."""
    if name not in _evaluation_results:
        if name in _running_evaluations:
            status = _running_evaluations[name]["status"]
            raise HTTPException(
                status_code=400,
                detail=f"Evaluation '{name}' is {status}. Results not available yet.",
            )
        raise HTTPException(status_code=404, detail=f"Evaluation '{name}' not found")
    
    report = _evaluation_results[name]
    return report.to_dict()


@router.get("/evaluation/results/{name}/summary")
async def get_evaluation_summary(
    name: str,
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get text summary of evaluation results."""
    if name not in _evaluation_results:
        raise HTTPException(status_code=404, detail=f"Evaluation '{name}' not found")
    
    report = _evaluation_results[name]
    return {"summary": report.summary()}


@router.get("/evaluation/list")
async def list_evaluations(
    user: AuthenticatedUser = Depends(get_current_user),
):
    """List all evaluations (running and completed)."""
    evaluations = []
    
    for name, status in _running_evaluations.items():
        evaluations.append({
            "name": name,
            "status": status["status"],
            "has_results": name in _evaluation_results,
        })
    
    return {"evaluations": evaluations}


@router.get("/evaluation/sample-dataset")
async def get_sample_dataset(
    user: AuthenticatedUser = Depends(get_current_user),
):
    """Get the sample evaluation dataset."""
    dataset = create_sample_dataset()
    return {
        "name": dataset.name,
        "total_cases": len(dataset),
        "categories": list(set(tc.category for tc in dataset)),
        "difficulties": list(set(tc.difficulty for tc in dataset)),
        "test_cases": [tc.to_dict() for tc in dataset],
    }
