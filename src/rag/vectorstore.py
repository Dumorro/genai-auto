"""Vector store using PostgreSQL + pgvector."""

import json
from typing import List, Dict, Any
from uuid import uuid4
from datetime import datetime

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.config import get_settings
from src.rag.embeddings import EmbeddingService

logger = structlog.get_logger()
settings = get_settings()


class SearchResult:
    """Result from vector similarity search."""

    def __init__(
        self,
        content: str,
        score: float,
        metadata: dict,
        document_id: str,
        source: str = None,
    ):
        self.content = content
        self.score = score
        self.metadata = metadata
        self.document_id = document_id
        self.source = source

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "score": self.score,
            "metadata": self.metadata,
            "document_id": self.document_id,
            "source": self.source,
        }


class VectorStore:
    """PostgreSQL + pgvector based vector store."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()
        self.table_name = "document_embeddings"

    async def add_documents(
        self,
        contents: List[str],
        metadatas: List[dict] = None,
        source: str = None,
        document_type: str = "manual",
        document_id: str = None,
    ) -> Dict[str, Any]:
        """Add documents to the vector store.
        
        Args:
            contents: List of text contents to store
            metadatas: List of metadata dicts for each content
            source: Source identifier (filename, URL, etc.)
            document_type: Type of document (manual, spec, guide)
            document_id: Optional parent document ID
            
        Returns:
            Dict with document_id and count of chunks added
        """
        document_id = document_id or str(uuid4())
        metadatas = metadatas or [{}] * len(contents)

        logger.info(
            "Adding documents to vector store",
            count=len(contents),
            source=source,
            document_type=document_type,
        )

        # Generate embeddings
        embedding_result = await self.embedding_service.embed_texts(contents)

        # Insert into database
        chunks_added = 0
        for i, (content, embedding, metadata) in enumerate(
            zip(contents, embedding_result.embeddings, metadatas)
        ):
            chunk_metadata = {
                **metadata,
                "document_id": document_id,
                "chunk_index": i,
                "source": source,
                "indexed_at": datetime.utcnow().isoformat(),
            }

            # Convert embedding list to PostgreSQL vector format
            import json
            embedding_str = f"[{','.join(map(str, embedding))}]"
            
            await self.db.execute(
                text("""
                    INSERT INTO document_embeddings 
                    (id, content, doc_metadata, embedding, source, document_type)
                    VALUES (:id, :content, CAST(:doc_metadata AS jsonb), CAST(:embedding AS vector), :source, :document_type)
                """),
                {
                    "id": str(uuid4()),
                    "content": content,
                    "doc_metadata": json.dumps(chunk_metadata),
                    "embedding": embedding_str,
                    "source": source,
                    "document_type": document_type,
                },
            )
            chunks_added += 1

        await self.db.commit()

        logger.info(
            "Documents added to vector store",
            document_id=document_id,
            chunks_added=chunks_added,
            tokens_used=embedding_result.tokens_used,
        )

        return {
            "document_id": document_id,
            "chunks_added": chunks_added,
            "tokens_used": embedding_result.tokens_used,
        }

    async def search(
        self,
        query: str,
        top_k: int = 5,
        document_type: str = None,
        source: str = None,
        min_score: float = 0.0,
    ) -> List[SearchResult]:
        """Search for similar documents.
        
        Args:
            query: Search query text
            top_k: Number of results to return
            document_type: Filter by document type
            source: Filter by source
            min_score: Minimum similarity score (0-1)
            
        Returns:
            List of SearchResult objects
        """
        logger.info(
            "Searching vector store",
            query_length=len(query),
            top_k=top_k,
            document_type=document_type,
        )

        # Generate query embedding
        query_embedding = await self.embedding_service.embed_query(query)

        # Build query with filters
        # Convert embedding to PostgreSQL vector format
        embedding_str = f"[{','.join(map(str, query_embedding))}]"
        
        sql = """
            SELECT 
                id,
                content, 
                doc_metadata as metadata, 
                source, 
                document_type,
                1 - (embedding <=> CAST(:embedding AS vector)) as score
            FROM document_embeddings
            WHERE 1=1
        """
        params = {
            "embedding": embedding_str,
            "top_k": top_k,
            "min_score": min_score,
        }

        if document_type:
            sql += " AND document_type = :document_type"
            params["document_type"] = document_type

        if source:
            sql += " AND source = :source"
            params["source"] = source

        sql += """
            AND 1 - (embedding <=> CAST(:embedding AS vector)) >= :min_score
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
        """

        result = await self.db.execute(text(sql), params)
        rows = result.fetchall()

        results = [
            SearchResult(
                content=row.content,
                score=float(row.score),
                metadata=row.metadata or {},
                document_id=str(row.id),
                source=row.source,
            )
            for row in rows
        ]

        logger.info(
            "Search completed",
            results_count=len(results),
            top_score=results[0].score if results else 0,
        )

        return results

    async def delete_by_source(self, source: str) -> int:
        """Delete all documents from a specific source.
        
        Returns:
            Number of documents deleted
        """
        result = await self.db.execute(
            text("DELETE FROM document_embeddings WHERE source = :source"),
            {"source": source},
        )
        await self.db.commit()
        
        deleted = result.rowcount
        logger.info("Documents deleted", source=source, count=deleted)
        
        return deleted

    async def delete_by_document_id(self, document_id: str) -> int:
        """Delete all chunks of a document.
        
        Returns:
            Number of chunks deleted
        """
        result = await self.db.execute(
            text("""
                DELETE FROM document_embeddings 
                WHERE doc_metadata->>'document_id' = :document_id
            """),
            {"document_id": document_id},
        )
        await self.db.commit()
        
        deleted = result.rowcount
        logger.info("Document deleted", document_id=document_id, chunks=deleted)
        
        return deleted

    async def list_sources(self) -> List[dict]:
        """List all document sources in the store."""
        result = await self.db.execute(
            text("""
                SELECT 
                    source,
                    document_type,
                    COUNT(*) as chunk_count,
                    MIN(created_at) as first_indexed,
                    MAX(created_at) as last_indexed
                FROM document_embeddings
                GROUP BY source, document_type
                ORDER BY last_indexed DESC
            """)
        )
        rows = result.fetchall()
        
        return [
            {
                "source": row.source,
                "document_type": row.document_type,
                "chunk_count": row.chunk_count,
                "first_indexed": row.first_indexed.isoformat() if row.first_indexed else None,
                "last_indexed": row.last_indexed.isoformat() if row.last_indexed else None,
            }
            for row in rows
        ]

    async def get_stats(self) -> dict:
        """Get vector store statistics."""
        result = await self.db.execute(
            text("""
                SELECT 
                    COUNT(*) as total_chunks,
                    COUNT(DISTINCT source) as total_sources,
                    COUNT(DISTINCT document_type) as total_types
                FROM document_embeddings
            """)
        )
        row = result.fetchone()
        
        return {
            "total_chunks": row.total_chunks,
            "total_sources": row.total_sources,
            "total_document_types": row.total_types,
        }
