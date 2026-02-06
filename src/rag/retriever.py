"""
RAG Retriever with integrated metrics tracking.
"""

import time
from typing import List, Dict
from ..api.metrics import track_rag_retrieval


class RAGRetriever:
    """
    Vector store retriever with automatic metrics tracking.
    """
    
    def __init__(self, vector_store, embeddings):
        self.vector_store = vector_store
        self.embeddings = embeddings
    
    async def retrieve(
        self,
        query: str,
        agent: str,
        document_type: str = "general",
        top_k: int = 5
    ) -> List[Dict]:
        """
        Retrieve relevant documents with automatic metrics tracking.
        
        Args:
            query: Search query
            agent: Agent making the request (specs/maintenance/troubleshoot)
            document_type: Type of documents to search (manual/spec/faq/guide/troubleshoot)
            top_k: Number of results to return
        
        Returns:
            List of documents with content and similarity scores
        """
        start_time = time.time()
        
        # Perform vector search
        results = await self.vector_store.similarity_search_with_score(
            query=query,
            k=top_k,
            filter={"document_type": document_type} if document_type != "general" else None
        )
        
        search_latency_ms = (time.time() - start_time) * 1000
        
        # Extract similarity scores
        similarity_scores = [score for _, score in results]
        
        # Track metrics
        track_rag_retrieval(
            agent=agent,
            document_type=document_type,
            similarity_scores=similarity_scores,
            search_latency_ms=search_latency_ms
        )
        
        # Format results
        documents = [
            {
                "content": doc.page_content,
                "metadata": doc.metadata,
                "similarity": score
            }
            for doc, score in results
        ]
        
        return documents
    
    async def retrieve_with_threshold(
        self,
        query: str,
        agent: str,
        document_type: str = "general",
        top_k: int = 5,
        min_similarity: float = 0.7
    ) -> List[Dict]:
        """
        Retrieve documents with minimum similarity threshold.
        
        Args:
            query: Search query
            agent: Agent making the request
            document_type: Type of documents
            top_k: Number of results
            min_similarity: Minimum similarity score (0-1)
        
        Returns:
            Filtered list of documents above threshold
        """
        results = await self.retrieve(
            query=query,
            agent=agent,
            document_type=document_type,
            top_k=top_k
        )
        
        # Filter by threshold
        filtered = [doc for doc in results if doc["similarity"] >= min_similarity]
        
        return filtered


# ============================================================================
# USAGE EXAMPLE
# ============================================================================

"""
from rag.retriever import RAGRetriever

# Initialize
retriever = RAGRetriever(vector_store, embeddings)

# Retrieve with auto-metrics
results = await retriever.retrieve(
    query="How to change oil?",
    agent="specs",
    document_type="manual",
    top_k=5
)

# Metrics tracked automatically:
# - rag_similarity_score (for each retrieved doc)
# - rag_documents_retrieved_total
# - rag_search_latency_ms

# Results:
[
    {
        "content": "Oil change procedure...",
        "metadata": {"source": "manual.pdf", "page": 42},
        "similarity": 0.89
    },
    ...
]
"""
