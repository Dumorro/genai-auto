"""Document ingestion pipeline for RAG system."""

from typing import Optional
from uuid import uuid4
import io

import structlog
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from src.api.config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DocumentIngestionPipeline:
    """Pipeline for ingesting documents into the vector store."""

    def __init__(self, db: AsyncSession):
        self.db = db
        # Use OpenRouter for embeddings
        self.embeddings = OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
        )

    async def ingest(
        self,
        content: bytes,
        filename: str,
        content_type: str,
        document_type: str = "manual",
    ) -> dict:
        """Ingest a document into the vector store.

        Args:
            content: Raw document bytes
            filename: Original filename
            content_type: MIME type
            document_type: Classification (manual, spec, guide)

        Returns:
            Dict with document_id and chunks_created count
        """
        logger.info(
            "Starting document ingestion",
            filename=filename,
            content_type=content_type,
            document_type=document_type,
        )

        # Extract text based on content type
        text_content = await self._extract_text(content, content_type)

        # Split into chunks
        chunks = self.text_splitter.split_text(text_content)
        logger.info("Document split into chunks", chunk_count=len(chunks))

        # Generate embeddings for all chunks
        embeddings = await self.embeddings.aembed_documents(chunks)

        # Store in database
        document_id = uuid4()
        chunks_created = 0

        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            await self.db.execute(
                text("""
                    INSERT INTO document_embeddings (id, content, metadata, embedding, source, document_type)
                    VALUES (:id, :content, :metadata, :embedding, :source, :document_type)
                """),
                {
                    "id": str(uuid4()),
                    "content": chunk,
                    "metadata": {
                        "document_id": str(document_id),
                        "chunk_index": i,
                        "filename": filename,
                    },
                    "embedding": embedding,
                    "source": filename,
                    "document_type": document_type,
                },
            )
            chunks_created += 1

        await self.db.commit()

        logger.info(
            "Document ingestion complete",
            document_id=str(document_id),
            chunks_created=chunks_created,
        )

        return {
            "document_id": document_id,
            "chunks_created": chunks_created,
        }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_type: Optional[str] = None,
    ) -> list[dict]:
        """Search for relevant document chunks.

        Args:
            query: Search query
            top_k: Number of results to return
            document_type: Optional filter by document type

        Returns:
            List of matching chunks with scores
        """
        # Generate query embedding
        query_embedding = await self.embeddings.aembed_query(query)

        # Build query
        sql = """
            SELECT content, metadata, source, document_type,
                   1 - (embedding <=> :embedding::vector) as score
            FROM document_embeddings
        """

        params = {"embedding": query_embedding, "top_k": top_k}

        if document_type:
            sql += " WHERE document_type = :document_type"
            params["document_type"] = document_type

        sql += " ORDER BY embedding <=> :embedding::vector LIMIT :top_k"

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        return [
            {
                "content": row.content,
                "metadata": row.metadata,
                "source": row.source,
                "document_type": row.document_type,
                "score": float(row.score),
            }
            for row in rows
        ]

    async def _extract_text(self, content: bytes, content_type: str) -> str:
        """Extract text from various document formats."""
        if content_type == "text/plain":
            return content.decode("utf-8")

        elif content_type == "application/pdf":
            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(content))
                text = ""
                for page in reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except Exception as e:
                logger.error("PDF extraction failed", error=str(e))
                raise ValueError(f"Failed to extract text from PDF: {e}")

        elif content_type in [
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "application/msword",
        ]:
            try:
                from docx import Document

                doc = Document(io.BytesIO(content))
                return "\n".join([para.text for para in doc.paragraphs])
            except Exception as e:
                logger.error("DOCX extraction failed", error=str(e))
                raise ValueError(f"Failed to extract text from DOCX: {e}")

        else:
            # Try to decode as text
            try:
                return content.decode("utf-8")
            except UnicodeDecodeError:
                raise ValueError(f"Unsupported content type: {content_type}")
