"""Specs Agent - Handles technical documentation and specifications queries using RAG."""

from typing import TYPE_CHECKING

import structlog
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate

from src.api.config import get_settings

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
    """

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            api_key=settings.openai_api_key,
            temperature=0.1,
        )
        self.embeddings = OpenAIEmbeddings(
            model=settings.openai_embedding_model,
            api_key=settings.openai_api_key,
        )

        self.system_prompt = """You are a knowledgeable automotive technical specialist assistant.
Your role is to help customers understand their vehicle's specifications, features, and documentation.

When answering questions:
1. Be precise and technical when needed, but explain in accessible terms
2. Reference specific manual sections or documentation when available
3. If you're not sure about something, say so rather than guessing
4. Provide safety warnings when relevant
5. Suggest consulting a professional for complex technical issues

Context from documentation:
{context}

If no relevant context is found, provide general guidance and recommend checking the owner's manual."""

    async def process(self, state: "AgentState") -> str:
        """Process a specs/documentation query."""
        last_message = state["messages"][-1]
        user_query = (
            last_message.get("content", "")
            if isinstance(last_message, dict)
            else str(last_message)
        )

        logger.info(
            "Processing specs query",
            session_id=state["session_id"],
            query_length=len(user_query),
        )

        # TODO: Implement actual vector search
        # For now, using placeholder context
        context = await self._retrieve_context(user_query)

        # Generate response with context
        prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            ("human", "{query}"),
        ])

        chain = prompt | self.llm

        response = await chain.ainvoke({
            "context": context,
            "query": user_query,
        })

        return response.content

    async def _retrieve_context(self, query: str, top_k: int = 5) -> str:
        """Retrieve relevant context from vector store.

        TODO: Implement actual pgvector search.
        """
        # Placeholder - will be replaced with actual vector search
        logger.info("Retrieving context for query", query_length=len(query))

        # For now, return empty context
        # In production, this would query pgvector
        return "No relevant documentation found in the database. Providing general guidance."

    async def embed_query(self, query: str) -> list[float]:
        """Generate embeddings for a query."""
        return await self.embeddings.aembed_query(query)
