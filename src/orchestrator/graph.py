"""LangGraph workflow orchestrator."""

from typing import TypedDict, List, Optional, Literal, Annotated
import operator

import structlog
from langgraph.graph import StateGraph, END
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from src.api.config import get_settings
from src.agents.specs.agent import SpecsAgent
from src.agents.maintenance.agent import MaintenanceAgent
from src.agents.troubleshoot.agent import TroubleshootAgent

logger = structlog.get_logger()
settings = get_settings()


class AgentState(TypedDict):
    """State schema for the agent workflow."""

    messages: Annotated[List[dict], operator.add]
    session_id: str
    customer_id: Optional[str]
    vehicle_id: Optional[str]
    metadata: dict
    current_agent: Optional[str]
    context: dict


def create_llm() -> ChatOpenAI:
    """Create LLM instance using OpenRouter."""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        temperature=0.1,
        default_headers={
            "HTTP-Referer": "https://github.com/genai-auto",
            "X-Title": "GenAI Auto",
        },
    )


class Orchestrator:
    """Main orchestrator that routes requests to appropriate agents."""

    def __init__(self):
        self.llm = create_llm()
        self.specs_agent = SpecsAgent()
        self.maintenance_agent = MaintenanceAgent()
        self.troubleshoot_agent = TroubleshootAgent()

    async def classify_intent(self, state: AgentState) -> AgentState:
        """Classify user intent and determine which agent to use."""
        logger.info("Classifying intent", session_id=state["session_id"])

        last_message = state["messages"][-1]
        user_input = last_message.get("content", "") if isinstance(last_message, dict) else str(last_message)

        classification_prompt = f"""Analyze the following user message and classify it into one of these categories:

1. SPECS - Questions about vehicle specifications, manuals, technical documentation, features, how things work
2. MAINTENANCE - Requests to schedule service, book appointments, check service history, maintenance reminders
3. TROUBLESHOOT - Vehicle problems, error messages, diagnostic questions, something not working

User message: {user_input}

Respond with only one word: SPECS, MAINTENANCE, or TROUBLESHOOT"""

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an intent classifier for an automotive customer service system."),
            HumanMessage(content=classification_prompt),
        ])

        intent = response.content.strip().upper()

        if intent not in ["SPECS", "MAINTENANCE", "TROUBLESHOOT"]:
            intent = "SPECS"  # Default to specs for general questions

        logger.info("Intent classified", intent=intent, session_id=state["session_id"])

        state["current_agent"] = intent.lower()
        state["context"]["classified_intent"] = intent

        return state

    async def route_to_agent(self, state: AgentState) -> Literal["specs", "maintenance", "troubleshoot"]:
        """Route to the appropriate agent based on classification."""
        return state.get("current_agent", "specs")

    async def specs_node(self, state: AgentState) -> AgentState:
        """Handle specs/documentation queries."""
        logger.info("Processing with Specs Agent", session_id=state["session_id"])
        response = await self.specs_agent.process(state)
        state["messages"].append({"role": "assistant", "content": response})
        return state

    async def maintenance_node(self, state: AgentState) -> AgentState:
        """Handle maintenance/scheduling requests."""
        logger.info("Processing with Maintenance Agent", session_id=state["session_id"])
        response = await self.maintenance_agent.process(state)
        state["messages"].append({"role": "assistant", "content": response})
        return state

    async def troubleshoot_node(self, state: AgentState) -> AgentState:
        """Handle troubleshooting/diagnostic queries."""
        logger.info("Processing with Troubleshoot Agent", session_id=state["session_id"])
        response = await self.troubleshoot_agent.process(state)
        state["messages"].append({"role": "assistant", "content": response})
        return state


def create_workflow() -> StateGraph:
    """Create and compile the LangGraph workflow."""
    orchestrator = Orchestrator()

    # Define the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("classify", orchestrator.classify_intent)
    workflow.add_node("specs", orchestrator.specs_node)
    workflow.add_node("maintenance", orchestrator.maintenance_node)
    workflow.add_node("troubleshoot", orchestrator.troubleshoot_node)

    # Set entry point
    workflow.set_entry_point("classify")

    # Add conditional routing
    workflow.add_conditional_edges(
        "classify",
        orchestrator.route_to_agent,
        {
            "specs": "specs",
            "maintenance": "maintenance",
            "troubleshoot": "troubleshoot",
        },
    )

    # All agents end after processing
    workflow.add_edge("specs", END)
    workflow.add_edge("maintenance", END)
    workflow.add_edge("troubleshoot", END)

    # Compile and return
    return workflow.compile()
