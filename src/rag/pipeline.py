"""Main RAG pipeline for document ingestion and retrieval."""

import io
from typing import List

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.rag.chunker import DocumentChunker, ChunkerConfig, ChunkingStrategy, auto_detect_strategy
from src.rag.embeddings import EmbeddingService
from src.rag.vectorstore import VectorStore, SearchResult

logger = structlog.get_logger()
settings = get_settings()


class DocumentLoader:
    """Load and extract text from various document formats."""

    @staticmethod
    async def load(
        content: bytes,
        filename: str,
        content_type: str = None,
    ) -> str:
        """Extract text from document.
        
        Supports:
        - Plain text (.txt)
        - PDF (.pdf)
        - Word documents (.docx)
        - Markdown (.md)
        """
        filename_lower = filename.lower()

        # Plain text
        if content_type == "text/plain" or filename_lower.endswith('.txt'):
            return content.decode('utf-8')

        # Markdown
        if filename_lower.endswith('.md'):
            return content.decode('utf-8')

        # PDF
        if content_type == "application/pdf" or filename_lower.endswith('.pdf'):
            return await DocumentLoader._extract_pdf(content)

        # Word documents
        if filename_lower.endswith('.docx') or content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]:
            return await DocumentLoader._extract_docx(content)

        # Try as text
        try:
            return content.decode('utf-8')
        except UnicodeDecodeError:
            raise ValueError(f"Unsupported file format: {filename}")

    @staticmethod
    async def _extract_pdf(content: bytes) -> str:
        """Extract text from PDF."""
        try:
            from pypdf import PdfReader
            
            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            
            for page_num, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(f"[Page {page_num + 1}]\n{page_text}")
            
            return "\n\n".join(text_parts)
            
        except Exception as e:
            logger.error("PDF extraction failed", error=str(e))
            raise ValueError(f"Failed to extract PDF: {e}")

    @staticmethod
    async def _extract_docx(content: bytes) -> str:
        """Extract text from Word document."""
        try:
            from docx import Document
            
            doc = Document(io.BytesIO(content))
            paragraphs = [para.text for para in doc.paragraphs if para.text.strip()]
            
            return "\n\n".join(paragraphs)
            
        except Exception as e:
            logger.error("DOCX extraction failed", error=str(e))
            raise ValueError(f"Failed to extract DOCX: {e}")


class RAGPipeline:
    """Complete RAG pipeline for document ingestion and retrieval."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.vectorstore = VectorStore(db)
        self.chunker = DocumentChunker()
        self.embedding_service = EmbeddingService()

    async def ingest_document(
        self,
        content: bytes,
        filename: str,
        content_type: str = None,
        document_type: str = "manual",
        chunking_strategy: ChunkingStrategy = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        metadata: dict = None,
    ) -> dict:
        """Ingest a document into the RAG system.
        
        Args:
            content: Raw document bytes
            filename: Original filename
            content_type: MIME type
            document_type: Classification (manual, spec, guide, faq)
            chunking_strategy: Override auto-detection
            chunk_size: Target chunk size
            chunk_overlap: Overlap between chunks
            metadata: Additional metadata to store
            
        Returns:
            Dict with ingestion results
        """
        logger.info(
            "Starting document ingestion",
            filename=filename,
            content_type=content_type,
            document_type=document_type,
        )

        # 1. Extract text from document
        text = await DocumentLoader.load(content, filename, content_type)
        
        if not text.strip():
            raise ValueError("Document appears to be empty")

        # 2. Determine chunking strategy
        strategy = chunking_strategy or auto_detect_strategy(text, filename)
        
        # 3. Configure and run chunker
        chunker_config = ChunkerConfig(
            strategy=strategy,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
        chunker = DocumentChunker(chunker_config)
        
        base_metadata = {
            "filename": filename,
            "content_type": content_type,
            "document_type": document_type,
            "original_length": len(text),
            **(metadata or {}),
        }
        
        chunks = chunker.chunk(text, metadata=base_metadata, strategy=strategy)

        # 4. Store in vector database
        result = await self.vectorstore.add_documents(
            contents=[c.content for c in chunks],
            metadatas=[c.metadata for c in chunks],
            source=filename,
            document_type=document_type,
        )

        logger.info(
            "Document ingestion complete",
            filename=filename,
            chunks_created=result["chunks_added"],
            tokens_used=result["tokens_used"],
        )

        return {
            "document_id": result["document_id"],
            "filename": filename,
            "document_type": document_type,
            "chunks_created": result["chunks_added"],
            "tokens_used": result["tokens_used"],
            "chunking_strategy": strategy.value,
            "original_length": len(text),
        }

    async def ingest_text(
        self,
        text: str,
        source: str,
        document_type: str = "manual",
        chunking_strategy: ChunkingStrategy = None,
        metadata: dict = None,
    ) -> dict:
        """Ingest raw text into the RAG system.
        
        Args:
            text: Text content to ingest
            source: Source identifier
            document_type: Classification
            chunking_strategy: Chunking strategy to use
            metadata: Additional metadata
            
        Returns:
            Dict with ingestion results
        """
        content = text.encode('utf-8')
        return await self.ingest_document(
            content=content,
            filename=source,
            content_type="text/plain",
            document_type=document_type,
            chunking_strategy=chunking_strategy,
            metadata=metadata,
        )

    async def query(
        self,
        query: str,
        top_k: int = 5,
        document_type: str = None,
        source: str = None,
        min_score: float = 0.5,
    ) -> List[SearchResult]:
        """Query the RAG system for relevant documents.
        
        Args:
            query: Search query
            top_k: Number of results
            document_type: Filter by type
            source: Filter by source
            min_score: Minimum similarity threshold
            
        Returns:
            List of relevant document chunks
        """
        return await self.vectorstore.search(
            query=query,
            top_k=top_k,
            document_type=document_type,
            source=source,
            min_score=min_score,
        )

    async def get_context(
        self,
        query: str,
        top_k: int = 5,
        max_tokens: int = 3000,
        document_type: str = None,
    ) -> str:
        """Get formatted context for LLM prompt.
        
        Args:
            query: User query
            top_k: Number of chunks to retrieve
            max_tokens: Approximate token limit for context
            document_type: Filter by document type
            
        Returns:
            Formatted context string for LLM
        """
        results = await self.query(
            query=query,
            top_k=top_k,
            document_type=document_type,
        )

        if not results:
            return "No relevant documents found in the knowledge base."

        # Build context with sources
        context_parts = []
        total_chars = 0
        max_chars = max_tokens * 4  # Rough token-to-char ratio

        for i, result in enumerate(results):
            chunk_text = f"[Source: {result.source}, Relevance: {result.score:.2f}]\n{result.content}"
            
            if total_chars + len(chunk_text) > max_chars:
                break
                
            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n\n---\n\n".join(context_parts)

    async def delete_document(self, source: str) -> int:
        """Delete a document from the knowledge base.
        
        Args:
            source: Source/filename to delete
            
        Returns:
            Number of chunks deleted
        """
        return await self.vectorstore.delete_by_source(source)

    async def list_documents(self) -> List[dict]:
        """List all documents in the knowledge base."""
        return await self.vectorstore.list_sources()

    async def get_stats(self) -> dict:
        """Get knowledge base statistics."""
        return await self.vectorstore.get_stats()
