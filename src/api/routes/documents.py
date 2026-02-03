"""Document management endpoints for RAG system."""

from typing import List, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_db
from src.agents.specs.ingestion import DocumentIngestionPipeline

logger = structlog.get_logger()
router = APIRouter()


class DocumentMetadata(BaseModel):
    """Document metadata model."""

    source: str = Field(..., description="Document source/filename")
    document_type: str = Field(..., description="Type of document (manual, spec, guide)")
    tags: List[str] = Field(default_factory=list, description="Document tags")


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""

    document_id: UUID
    chunks_created: int
    status: str


class SearchRequest(BaseModel):
    """Vector search request."""

    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, description="Number of results to return")
    document_type: Optional[str] = Field(default=None, description="Filter by document type")


class SearchResult(BaseModel):
    """Single search result."""

    content: str
    score: float
    metadata: dict


class SearchResponse(BaseModel):
    """Vector search response."""

    results: List[SearchResult]
    query: str


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = "manual",
    db: AsyncSession = Depends(get_db),
):
    """Upload and process a document for RAG."""
    logger.info(
        "Processing document upload",
        filename=file.filename,
        content_type=file.content_type,
    )

    try:
        # Read file content
        content = await file.read()

        # Initialize ingestion pipeline
        pipeline = DocumentIngestionPipeline(db)

        # Process document
        result = await pipeline.ingest(
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            document_type=document_type,
        )

        return DocumentUploadResponse(
            document_id=result["document_id"],
            chunks_created=result["chunks_created"],
            status="success",
        )

    except Exception as e:
        logger.error("Document upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.post("/documents/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db),
):
    """Search documents using vector similarity."""
    logger.info("Processing search request", query=request.query[:50])

    try:
        pipeline = DocumentIngestionPipeline(db)
        results = await pipeline.search(
            query=request.query,
            top_k=request.top_k,
            document_type=request.document_type,
        )

        return SearchResponse(
            results=[
                SearchResult(
                    content=r["content"],
                    score=r["score"],
                    metadata=r["metadata"],
                )
                for r in results
            ],
            query=request.query,
        )

    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/documents")
async def list_documents(
    document_type: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """List uploaded documents."""
    # TODO: Implement document listing
    return {"documents": [], "total": 0}
