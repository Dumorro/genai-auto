"""Document management endpoints for RAG system."""

from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_db
from src.api.auth import get_current_user, get_optional_user, AuthenticatedUser
from src.rag.pipeline import RAGPipeline
from src.rag.chunker import ChunkingStrategy

logger = structlog.get_logger()
router = APIRouter()


# ============== Request/Response Models ==============

class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    
    document_id: str
    filename: str
    document_type: str
    chunks_created: int
    tokens_used: int
    chunking_strategy: str


class TextIngestionRequest(BaseModel):
    """Request to ingest raw text."""
    
    text: str = Field(..., description="Text content to ingest")
    source: str = Field(..., description="Source identifier")
    document_type: str = Field(default="manual", description="Document type")
    chunking_strategy: Optional[str] = Field(default=None, description="Chunking strategy")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class SearchRequest(BaseModel):
    """Vector search request."""
    
    query: str = Field(..., description="Search query")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    document_type: Optional[str] = Field(default=None, description="Filter by type")
    source: Optional[str] = Field(default=None, description="Filter by source")
    min_score: float = Field(default=0.5, ge=0, le=1, description="Minimum similarity")


class SearchResult(BaseModel):
    """Single search result."""
    
    content: str
    score: float
    metadata: dict
    source: Optional[str]


class SearchResponse(BaseModel):
    """Vector search response."""
    
    results: List[SearchResult]
    query: str
    total: int


class DocumentInfo(BaseModel):
    """Document information."""
    
    source: str
    document_type: str
    chunk_count: int
    first_indexed: Optional[str]
    last_indexed: Optional[str]


class KnowledgeBaseStats(BaseModel):
    """Knowledge base statistics."""
    
    total_chunks: int
    total_sources: int
    total_document_types: int


# ============== Endpoints ==============

@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(default="manual"),
    chunk_size: int = Form(default=1000),
    chunk_overlap: int = Form(default=200),
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload and ingest a document into the knowledge base.
    
    Supported formats:
    - PDF (.pdf)
    - Word (.docx)
    - Text (.txt)
    - Markdown (.md)
    """
    logger.info(
        "Document upload",
        filename=file.filename,
        content_type=file.content_type,
        user=user.email,
    )

    try:
        content = await file.read()
        
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Empty file")
        
        if len(content) > 50 * 1024 * 1024:  # 50MB limit
            raise HTTPException(status_code=400, detail="File too large (max 50MB)")

        pipeline = RAGPipeline(db)
        result = await pipeline.ingest_document(
            content=content,
            filename=file.filename,
            content_type=file.content_type,
            document_type=document_type,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            metadata={"uploaded_by": user.email},
        )

        return DocumentUploadResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Document upload failed", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")


@router.post("/documents/ingest-text", response_model=DocumentUploadResponse)
async def ingest_text(
    request: TextIngestionRequest,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Ingest raw text into the knowledge base."""
    logger.info(
        "Text ingestion",
        source=request.source,
        text_length=len(request.text),
        user=user.email,
    )

    try:
        strategy = None
        if request.chunking_strategy:
            strategy = ChunkingStrategy(request.chunking_strategy)

        pipeline = RAGPipeline(db)
        result = await pipeline.ingest_text(
            text=request.text,
            source=request.source,
            document_type=request.document_type,
            chunking_strategy=strategy,
            metadata={**request.metadata, "uploaded_by": user.email},
        )

        return DocumentUploadResponse(**result)

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error("Text ingestion failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/search", response_model=SearchResponse)
async def search_documents(
    request: SearchRequest,
    user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Search the knowledge base using semantic similarity."""
    logger.info(
        "Document search",
        query_length=len(request.query),
        top_k=request.top_k,
    )

    try:
        pipeline = RAGPipeline(db)
        results = await pipeline.query(
            query=request.query,
            top_k=request.top_k,
            document_type=request.document_type,
            source=request.source,
            min_score=request.min_score,
        )

        return SearchResponse(
            results=[
                SearchResult(
                    content=r.content,
                    score=r.score,
                    metadata=r.metadata,
                    source=r.source,
                )
                for r in results
            ],
            query=request.query,
            total=len(results),
        )

    except Exception as e:
        logger.error("Search failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=List[DocumentInfo])
async def list_documents(
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all documents in the knowledge base."""
    pipeline = RAGPipeline(db)
    docs = await pipeline.list_documents()
    return [DocumentInfo(**doc) for doc in docs]


@router.get("/documents/stats", response_model=KnowledgeBaseStats)
async def get_stats(
    user: Optional[AuthenticatedUser] = Depends(get_optional_user),
    db: AsyncSession = Depends(get_db),
):
    """Get knowledge base statistics."""
    pipeline = RAGPipeline(db)
    stats = await pipeline.get_stats()
    return KnowledgeBaseStats(**stats)


@router.delete("/documents/{source:path}")
async def delete_document(
    source: str,
    user: AuthenticatedUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a document from the knowledge base."""
    logger.info(
        "Document deletion",
        source=source,
        user=user.email,
    )

    pipeline = RAGPipeline(db)
    deleted = await pipeline.delete_document(source)

    if deleted == 0:
        raise HTTPException(status_code=404, detail="Document not found")

    return {
        "message": "Document deleted",
        "source": source,
        "chunks_deleted": deleted,
    }
