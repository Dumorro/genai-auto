"""Troubleshoot Agent - Handles diagnostic and problem-solving queries."""

from typing import TYPE_CHECKING, Optional
from enum import Enum

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from pydantic import BaseModel, Field

from src.api.config import get_settings

if TYPE_CHECKING:
    from src.orchestrator.graph import AgentState

logger = structlog.get_logger()
settings = get_settings()


class Severity(str, Enum):
    """Issue severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DiagnosticResult(BaseModel):
    """Result of diagnostic analysis."""

    symptoms: list[str] = Field(description="Identified symptoms")
    possible_causes: list[str] = Field(description="Possible causes")
    recommended_actions: list[str] = Field(description="Recommended actions")
    severity: Severity = Field(description="Issue severity level")
    requires_professional: bool = Field(description="Whether professional service is needed")
    safety_warning: Optional[str] = Field(default=None, description="Safety warning if applicable")


# Diagnostic decision trees for common issues
DIAGNOSTIC_TREES = {
    "engine_warning_light": {
        "questions": [
            "Is the light steady or flashing?",
            "Have you noticed any changes in engine performance?",
            "When did you first notice the light?",
            "Have you recently refueled?",
        ],
        "common_causes": [
            "Loose gas cap",
            "Oxygen sensor issue",
            "Catalytic converter problem",
            "Mass airflow sensor",
            "Spark plugs/ignition coils",
        ],
    },
    "brake_issues": {
        "questions": [
            "Do you hear squealing, grinding, or other noises when braking?",
            "Does the brake pedal feel soft, spongy, or does it go to the floor?",
            "Does the vehicle pull to one side when braking?",
            "Do you feel vibration in the steering wheel when braking?",
        ],
        "common_causes": [
            "Worn brake pads",
            "Warped brake rotors",
            "Low brake fluid",
            "Air in brake lines",
            "Stuck caliper",
        ],
    },
    "starting_problems": {
        "questions": [
            "Does the engine crank but not start?",
            "Do you hear a clicking sound?",
            "Are the dashboard lights dim or flickering?",
            "Has the vehicle been sitting unused for a while?",
        ],
        "common_causes": [
            "Dead or weak battery",
            "Corroded battery terminals",
            "Faulty starter motor",
            "Fuel delivery issue",
            "Ignition switch problem",
        ],
    },
    "overheating": {
        "questions": [
            "Is the temperature gauge in the red zone?",
            "Do you see steam or smell coolant?",
            "Is the AC working properly?",
            "When was the coolant last checked/changed?",
        ],
        "common_causes": [
            "Low coolant level",
            "Thermostat failure",
            "Water pump issue",
            "Radiator blockage",
            "Cooling fan malfunction",
        ],
    },
    "strange_noises": {
        "questions": [
            "Where does the noise come from (front, rear, engine)?",
            "When does it occur (starting, driving, braking, turning)?",
            "How would you describe the sound (squealing, grinding, clunking, rattling)?",
            "Does it happen at certain speeds?",
        ],
        "common_causes": [
            "Worn belts",
            "Suspension components",
            "Exhaust system",
            "Wheel bearings",
            "CV joints",
        ],
    },
}


class TroubleshootAgent:
    """Agent for diagnosing vehicle problems and providing troubleshooting guidance.

    Uses diagnostic decision trees and LLM reasoning to:
    - Analyze symptoms
    - Guide through diagnostic questions
    - Identify possible causes
    - Recommend actions
    - Assess severity and safety concerns
    """

    def __init__(self):
        # Use OpenRouter for LLM
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.openrouter_api_key,
            base_url=settings.openrouter_base_url,
            temperature=0.2,
            default_headers={
                "HTTP-Referer": "https://github.com/genai-auto",
                "X-Title": "GenAI Auto - Troubleshoot Agent",
            },
        )

        self.system_prompt = """You are an expert automotive diagnostic assistant.
Your role is to help customers understand and troubleshoot vehicle problems.

IMPORTANT GUIDELINES:
1. SAFETY FIRST - Always warn about safety concerns
2. Ask clarifying questions to narrow down the problem
3. Explain technical concepts in simple terms
4. Be clear about what requires professional service vs. DIY fixes
5. Never encourage unsafe practices
6. If a problem could be dangerous (brakes, steering, etc.), emphasize getting professional help immediately

When diagnosing:
1. Identify symptoms from the customer's description
2. Ask targeted follow-up questions
3. Consider common causes for the symptoms
4. Provide a severity assessment
5. Recommend appropriate next steps

Known diagnostic patterns:
{diagnostic_context}

Remember: You're helping someone who may not be mechanically inclined. Be patient and thorough."""

    async def process(self, state: "AgentState") -> str:
        """Process a troubleshooting query."""
        last_message = state["messages"][-1]
        user_input = (
            last_message.get("content", "")
            if isinstance(last_message, dict)
            else str(last_message)
        )

        logger.info(
            "Processing troubleshoot request",
            session_id=state["session_id"],
            input_length=len(user_input),
        )

        # Identify relevant diagnostic tree
        diagnostic_context = self._get_diagnostic_context(user_input)

        # Build conversation history
        messages = [
            SystemMessage(content=self.system_prompt.format(diagnostic_context=diagnostic_context))
        ]

        for msg in state["messages"][:-1]:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    messages.append(HumanMessage(content=content))
                else:
                    messages.append(AIMessage(content=content))

        messages.append(HumanMessage(content=user_input))

        # Generate diagnostic response
        response = await self.llm.ainvoke(messages)

        # Check for critical safety issues
        safety_check = await self._check_safety_concerns(user_input, response.content)
        if safety_check:
            return f"⚠️ **SAFETY WARNING**: {safety_check}\n\n{response.content}"

        return response.content

    def _get_diagnostic_context(self, user_input: str) -> str:
        """Get relevant diagnostic tree context based on user input."""
        user_input_lower = user_input.lower()

        relevant_trees = []

        # Match keywords to diagnostic trees
        keyword_mapping = {
            "engine_warning_light": ["check engine", "engine light", "warning light", "dashboard light"],
            "brake_issues": ["brake", "braking", "stopping", "pedal"],
            "starting_problems": ["start", "starting", "won't turn on", "dead", "click"],
            "overheating": ["overheat", "hot", "temperature", "steam", "coolant"],
            "strange_noises": ["noise", "sound", "squeal", "grind", "rattle", "clunk"],
        }

        for tree_key, keywords in keyword_mapping.items():
            if any(kw in user_input_lower for kw in keywords):
                tree = DIAGNOSTIC_TREES[tree_key]
                relevant_trees.append(f"""
**{tree_key.replace('_', ' ').title()}:**
- Key questions: {', '.join(tree['questions'][:3])}
- Common causes: {', '.join(tree['common_causes'][:3])}
""")

        if relevant_trees:
            return "\n".join(relevant_trees)

        return "No specific diagnostic pattern matched. Use general troubleshooting approach."

    async def _check_safety_concerns(self, user_input: str, response: str) -> Optional[str]:
        """Check for safety-critical issues that need immediate attention."""
        safety_keywords = {
            "brake": "Brake issues can be life-threatening. If you're unsure about your brakes, do not drive the vehicle.",
            "steering": "Steering problems are dangerous. Have the vehicle towed if steering feels unsafe.",
            "smoke": "Smoke can indicate fire risk. Pull over safely and exit the vehicle if you see smoke.",
            "fire": "If you smell burning or see flames, stop immediately, exit the vehicle, and call emergency services.",
            "airbag": "Airbag warning lights indicate a serious safety system issue. Get professional inspection immediately.",
        }

        user_input_lower = user_input.lower()
        for keyword, warning in safety_keywords.items():
            if keyword in user_input_lower:
                return warning

        return None
