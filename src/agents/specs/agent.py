"""Specs Agent - Handles technical documentation queries using RAG."""

from typing import TYPE_CHECKING

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

from src.api.config import get_settings
from src.storage.database import async_session
from src.rag.pipeline import RAGPipeline

if TYPE_CHECKING:
    from src.orchestrator.graph import AgentState

logger = structlog.get_logger()
settings = get_settings()


class SpecsAgent:
    """Agent for handling technical specifications and documentation queries.

    Uses RAG (Retrieval Augmented Generation) to search through:
    - Vehicle manuals
    - Technical specifications
    - Feature guides
    - Maintenance schedules
    - FAQs
    """

    def __init__(self):
        # Use OpenRouter for LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.1,
            default_headers={
                "HTTP-Referer": "https://github.com/genai-auto",
                "X-Title": "GenAI Auto - Specs Agent",
            },
        )

        self.system_prompt = """You are a technical automotive specialist for the manufacturer.
Your role is to help customers understand vehicle specifications, features, and documentation.

INSTRUCTIONS:
1. Use ONLY the information provided in the context below to answer
2. If the information is not in the context, clearly state that you couldn't find it
3. Be precise and technical when necessary, but explain in accessible terms
4. Mention the source of information when relevant
5. Include safety warnings when appropriate
6. For complex issues, suggest consulting an authorized professional

KNOWLEDGE BASE CONTEXT:
{context}

---

If no relevant context was found, inform the customer that the information is not 
available in the knowledge base and suggest contacting technical support."""

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{query}"),
        ])

    async def process(self, state: "AgentState") -> str:
        """Process a specs/documentation query using RAG."""
        last_message = state["messages"][-1]
        user_query = (
            last_message.get("content", "")
            if isinstance(last_message, dict)
            else str(last_message)
        )

        logger.info(
            "Processing specs query with RAG",
            session_id=state["session_id"],
            query_length=len(user_query),
        )

        # Get relevant context from RAG
        context = await self._get_rag_context(user_query)

        # Generate response with context
        chain = self.prompt | self.llm

        response = await chain.ainvoke({
            "context": context,
            "query": user_query,
        })

        return response.content

    async def _get_rag_context(
        self,
        query: str,
        top_k: int = 5,
        max_tokens: int = 3000,
    ) -> str:
        """Retrieve relevant context from the RAG knowledge base."""
        try:
            async with async_session() as db:
                pipeline = RAGPipeline(db)
                context = await pipeline.get_context(
                    query=query,
                    top_k=top_k,
                    max_tokens=max_tokens,
                )
                return context

        except Exception as e:
            logger.error("RAG retrieval failed", error=str(e))
            return "Error accessing knowledge base. Please try again."

    async def search_knowledge_base(
        self,
        query: str,
        document_type: str = None,
        top_k: int = 5,
    ) -> list:
        """Search the knowledge base directly (for debugging/testing)."""
        async with async_session() as db:
            pipeline = RAGPipeline(db)
            results = await pipeline.query(
                query=query,
                document_type=document_type,
                top_k=top_k,
            )
            return [r.to_dict() for r in results]
