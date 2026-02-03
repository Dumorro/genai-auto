"""Chat endpoints for AI interaction."""

from typing import Optional
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.storage.database import get_db
from src.orchestrator.graph import create_workflow, AgentState

logger = structlog.get_logger()
router = APIRouter()


class ChatRequest(BaseModel):
    """Chat request model."""

    message: str = Field(..., description="User message")
    session_id: Optional[str] = Field(default=None, description="Session ID for conversation continuity")
    customer_id: Optional[UUID] = Field(default=None, description="Customer ID if known")
    vehicle_id: Optional[UUID] = Field(default=None, description="Vehicle ID if relevant")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class ChatResponse(BaseModel):
    """Chat response model."""

    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    agent_used: str = Field(..., description="Agent that handled the request")
    metadata: dict = Field(default_factory=dict, description="Response metadata")


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process a chat message through the multi-agent system."""
    session_id = request.session_id or str(uuid4())

    logger.info(
        "Processing chat request",
        session_id=session_id,
        message_length=len(request.message),
    )

    try:
        # Create the LangGraph workflow
        workflow = create_workflow()

        # Prepare initial state
        initial_state: AgentState = {
            "messages": [{"role": "user", "content": request.message}],
            "session_id": session_id,
            "customer_id": str(request.customer_id) if request.customer_id else None,
            "vehicle_id": str(request.vehicle_id) if request.vehicle_id else None,
            "metadata": request.metadata,
            "current_agent": None,
            "context": {},
        }

        # Run the workflow
        final_state = await workflow.ainvoke(initial_state)

        # Extract response
        response_message = final_state.get("messages", [])[-1]
        response_content = (
            response_message.get("content", "")
            if isinstance(response_message, dict)
            else str(response_message)
        )

        return ChatResponse(
            response=response_content,
            session_id=session_id,
            agent_used=final_state.get("current_agent", "orchestrator"),
            metadata=final_state.get("context", {}),
        )

    except Exception as e:
        logger.error("Chat processing failed", error=str(e), session_id=session_id)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/chat/history/{session_id}")
async def get_chat_history(
    session_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve chat history for a session."""
    # TODO: Implement conversation history retrieval
    return {"session_id": session_id, "messages": []}
