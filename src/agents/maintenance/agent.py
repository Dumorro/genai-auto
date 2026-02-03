"""Maintenance Agent - Handles scheduling and service appointments."""

from typing import TYPE_CHECKING
from datetime import datetime, timedelta

import structlog
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from src.api.config import get_settings

if TYPE_CHECKING:
    from src.orchestrator.graph import AgentState

logger = structlog.get_logger()
settings = get_settings()


# Define tools for the maintenance agent
@tool
def check_available_slots(service_type: str, preferred_date: str) -> str:
    """Check available appointment slots for a service.

    Args:
        service_type: Type of service (oil_change, tire_rotation, inspection, repair)
        preferred_date: Preferred date in YYYY-MM-DD format
    """
    # TODO: Integrate with actual scheduler API
    # Returning mock data for now
    return f"""Available slots for {service_type} on {preferred_date}:
- 09:00 AM
- 11:30 AM
- 02:00 PM
- 04:30 PM

Would you like me to book one of these slots?"""


@tool
def book_appointment(
    customer_name: str,
    service_type: str,
    date: str,
    time: str,
    vehicle_info: str = "",
) -> str:
    """Book a service appointment.

    Args:
        customer_name: Customer's full name
        service_type: Type of service requested
        date: Appointment date (YYYY-MM-DD)
        time: Appointment time (HH:MM)
        vehicle_info: Vehicle make/model/year (optional)
    """
    # TODO: Integrate with actual scheduler API and database
    confirmation_number = f"APT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    return f"""✅ Appointment Confirmed!

Confirmation Number: {confirmation_number}
Customer: {customer_name}
Service: {service_type}
Date: {date}
Time: {time}
{f'Vehicle: {vehicle_info}' if vehicle_info else ''}

Please arrive 10 minutes before your scheduled time.
You will receive a reminder 24 hours before your appointment."""


@tool
def get_service_history(customer_id: str) -> str:
    """Retrieve service history for a customer.

    Args:
        customer_id: Customer ID or identifier
    """
    # TODO: Query actual database
    return """Service History:

1. 2024-01-15 - Oil Change - $49.99 - Completed
2. 2023-10-20 - Tire Rotation - $29.99 - Completed
3. 2023-07-05 - Annual Inspection - $89.99 - Completed
4. 2023-03-12 - Brake Pad Replacement - $249.99 - Completed

Next recommended service: Oil Change (due in ~1,500 miles)"""


@tool
def cancel_appointment(confirmation_number: str) -> str:
    """Cancel an existing appointment.

    Args:
        confirmation_number: The appointment confirmation number
    """
    # TODO: Integrate with actual scheduler API
    return f"""Appointment {confirmation_number} has been cancelled.

If you'd like to reschedule, please let me know your preferred date and time."""


@tool
def get_service_pricing(service_type: str) -> str:
    """Get pricing information for a service.

    Args:
        service_type: Type of service to get pricing for
    """
    pricing = {
        "oil_change": "$49.99 - $79.99 (depending on oil type)",
        "tire_rotation": "$29.99",
        "inspection": "$89.99",
        "brake_service": "$149.99 - $399.99",
        "transmission_service": "$149.99 - $249.99",
        "air_filter": "$24.99 - $49.99",
        "battery_replacement": "$149.99 - $299.99",
    }

    service_key = service_type.lower().replace(" ", "_")
    price = pricing.get(service_key, "Please contact us for a quote on this service.")

    return f"Pricing for {service_type}: {price}\n\nPrices may vary based on vehicle make and model."


class MaintenanceAgent:
    """Agent for handling maintenance scheduling and service requests.

    Capabilities:
    - Check available appointment slots
    - Book service appointments
    - View service history
    - Cancel/reschedule appointments
    - Get service pricing
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
                "X-Title": "GenAI Auto - Maintenance Agent",
            },
        )

        self.tools = [
            check_available_slots,
            book_appointment,
            get_service_history,
            cancel_appointment,
            get_service_pricing,
        ]

        self.system_prompt = """You are a helpful automotive service scheduling assistant.
Your role is to help customers with:
- Scheduling service appointments
- Checking available time slots
- Viewing their service history
- Getting pricing information
- Canceling or rescheduling appointments

Guidelines:
1. Always confirm details before booking
2. Suggest appropriate services based on vehicle history
3. Be proactive about reminding customers of upcoming maintenance
4. If the customer hasn't provided vehicle information, ask for it
5. Be friendly and professional

Current date: {current_date}"""

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history", optional=True),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        self.agent = create_tool_calling_agent(self.llm, self.tools, self.prompt)
        self.agent_executor = AgentExecutor(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
        )

    async def process(self, state: "AgentState") -> str:
        """Process a maintenance/scheduling request."""
        last_message = state["messages"][-1]
        user_input = (
            last_message.get("content", "")
            if isinstance(last_message, dict)
            else str(last_message)
        )

        logger.info(
            "Processing maintenance request",
            session_id=state["session_id"],
            input_length=len(user_input),
        )

        # Build chat history from previous messages
        chat_history = []
        for msg in state["messages"][:-1]:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role == "user":
                    chat_history.append(HumanMessage(content=content))
                else:
                    chat_history.append(SystemMessage(content=content))

        result = await self.agent_executor.ainvoke({
            "input": user_input,
            "chat_history": chat_history,
            "current_date": datetime.now().strftime("%Y-%m-%d"),
        })

        return result["output"]
