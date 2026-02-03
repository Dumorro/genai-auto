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

        self.system_prompt = """Você é um especialista técnico automotivo da montadora.
Seu papel é ajudar os clientes a entender especificações, recursos e documentação dos veículos.

INSTRUÇÕES:
1. Use APENAS as informações fornecidas no contexto abaixo para responder
2. Se a informação não estiver no contexto, diga claramente que não encontrou
3. Seja preciso e técnico quando necessário, mas explique em termos acessíveis
4. Mencione a fonte da informação quando relevante
5. Inclua avisos de segurança quando apropriado
6. Para questões complexas, sugira consultar um profissional autorizado

CONTEXTO DA BASE DE CONHECIMENTO:
{context}

---

Se nenhum contexto relevante foi encontrado, informe ao cliente que a informação não está 
disponível na base de conhecimento e sugira contatar o suporte técnico."""

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
            return "Erro ao acessar a base de conhecimento. Por favor, tente novamente."

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
