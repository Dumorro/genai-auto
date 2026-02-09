# GenAI Auto -- Multi-Agent System Documentation

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Orchestrator](#orchestrator)
- [Specs Agent](#specs-agent)
- [Maintenance Agent](#maintenance-agent)
- [Troubleshoot Agent](#troubleshoot-agent)
- [Human Handoff](#human-handoff)
- [Configuration](#configuration)
- [Known Limitations](#known-limitations)

---

## Overview

GenAI Auto is a multi-agent automotive customer service system built on LangGraph and LangChain. It routes incoming user messages through an intent classifier and dispatches them to one of three specialized agents:

- **Specs Agent** -- Answers technical questions using Retrieval-Augmented Generation (RAG).
- **Maintenance Agent** -- Handles appointment scheduling and service inquiries via tool-calling.
- **Troubleshoot Agent** -- Diagnoses vehicle problems using decision trees and LLM reasoning.

A **Human Handoff** layer monitors confidence scores, safety signals, and explicit user requests to escalate conversations to live support when the automated agents are insufficient.

All agents share a common `AgentState` schema and communicate through the LangGraph `StateGraph` orchestrator defined in `src/orchestrator/graph.py`.

---

## Architecture

### Orchestration Flow

The following state diagram shows how a user message travels through the system:

```mermaid
stateDiagram-v2
    [*] --> classify_intent
    classify_intent --> route_to_agent

    state route_to_agent <<choice>>
    route_to_agent --> SpecsAgent : intent = SPECS
    route_to_agent --> MaintenanceAgent : intent = MAINTENANCE
    route_to_agent --> TroubleshootAgent : intent = TROUBLESHOOT

    SpecsAgent --> [*]
    MaintenanceAgent --> [*]
    TroubleshootAgent --> [*]

    note right of classify_intent
        LLM classifies user message
        into SPECS, MAINTENANCE,
        or TROUBLESHOOT.
        Confidence: 0.85 (matched)
        or 0.5 (fallback to SPECS).
    end note
```

### AgentState Schema

Every node in the graph operates on a shared `AgentState` TypedDict:

| Field           | Type                | Description                                      |
|-----------------|---------------------|--------------------------------------------------|
| `messages`      | `List[dict]`        | Conversation history (append-only via `operator.add`). |
| `session_id`    | `str`               | Unique identifier for the conversation session.  |
| `customer_id`   | `Optional[str]`     | Customer identifier, if authenticated.           |
| `vehicle_id`    | `Optional[str]`     | Vehicle identifier, if provided.                 |
| `metadata`      | `dict`              | Arbitrary metadata attached to the session.      |
| `current_agent` | `Optional[str]`     | The agent selected by intent classification (`specs`, `maintenance`, or `troubleshoot`). |
| `context`       | `dict`              | Mutable context bag; stores `classified_intent`, `confidence`, and `agent`. |

### LangGraph Node Topology

```
Entry Point
    |
    v
 [classify]  ----conditional----> [specs]        --> END
                   |               [maintenance]  --> END
                   |               [troubleshoot] --> END
```

Nodes are registered in `create_workflow()`:

- `classify` -- `orchestrator.classify_intent`
- `specs` -- `orchestrator.specs_node`
- `maintenance` -- `orchestrator.maintenance_node`
- `troubleshoot` -- `orchestrator.troubleshoot_node`

Routing is handled by `orchestrator.route_to_agent`, which reads `state["current_agent"]` and returns one of `"specs"`, `"maintenance"`, or `"troubleshoot"`.

---

## Orchestrator

**Source:** `src/orchestrator/graph.py`

### Intent Classification

The orchestrator sends the last user message to the LLM with the following system/human prompt pair:

- **System message:** `"You are an intent classifier for an automotive customer service system."`
- **Human message:** A prompt asking the LLM to respond with exactly one word -- `SPECS`, `MAINTENANCE`, or `TROUBLESHOOT`.

Classification categories:

| Intent          | Description                                                                 |
|-----------------|-----------------------------------------------------------------------------|
| `SPECS`         | Vehicle specifications, manuals, technical documentation, features, how things work. |
| `MAINTENANCE`   | Schedule service, book appointments, check service history, maintenance reminders.    |
| `TROUBLESHOOT`  | Vehicle problems, error messages, diagnostic questions, something not working.        |

### Confidence Scoring

| Scenario                              | Confidence |
|---------------------------------------|------------|
| LLM returns a valid intent            | **0.85**   |
| LLM returns unrecognized text (fallback to SPECS) | **0.50**   |

The confidence value is stored in `state["context"]["confidence"]` and is used downstream by the Human Handoff module to decide whether to escalate.

### LLM Configuration

The orchestrator's LLM is created by `create_llm()`:

- **Provider:** OpenRouter (`ChatOpenAI` with custom `base_url`)
- **Model:** Configurable via `LLM_MODEL` env var (default: `meta-llama/llama-3.1-8b-instruct:free`)
- **Temperature:** 0.1
- **Headers:** `HTTP-Referer: https://github.com/genai-auto`, `X-Title: GenAI Auto`

---

## Specs Agent

**Source:** `src/agents/specs/agent.py`

### Purpose

The Specs Agent answers questions about vehicle technical documentation using a RAG pipeline. It retrieves relevant chunks from the knowledge base and grounds its answers strictly in the retrieved context.

### Configuration

| Parameter     | Value  |
|---------------|--------|
| Temperature   | 0.1    |
| RAG `top_k`  | 5      |
| RAG `max_tokens` | 3000 |

### Knowledge Sources

The RAG pipeline searches across the following document types:

- Vehicle manuals
- Technical specifications
- Feature guides
- Maintenance schedules
- FAQs

### System Prompt Behavior

The Specs Agent system prompt enforces the following rules:

1. Use **only** the information provided in the retrieved context.
2. If the information is not in the context, clearly state that it could not be found.
3. Be precise and technical when necessary, but explain in accessible terms.
4. Mention the source of information when relevant.
5. Include safety warnings when appropriate.
6. For complex issues, suggest consulting an authorized professional.

When no relevant context is found, the agent informs the customer that the information is not available in the knowledge base and suggests contacting technical support.

### Processing Flow

1. Extract the last user message from `state["messages"]`.
2. Call `_get_rag_context(query, top_k=5, max_tokens=3000)` to retrieve relevant document chunks from the database via `RAGPipeline`.
3. Inject the retrieved context into the system prompt template.
4. Invoke the LLM chain (`prompt | llm`) with the context and query.
5. Return the LLM response content as a string.

If the RAG retrieval fails (database error, etc.), the context falls back to `"Error accessing knowledge base. Please try again."`.

### Example Interactions

**User:** "What is the towing capacity of the 2024 model?"

**Agent behavior:** Retrieves relevant sections from the technical specifications knowledge base, then answers strictly from that context.

**User:** "How do I use the lane departure warning system?"

**Agent behavior:** Retrieves feature guide content for the lane departure system and explains the feature in accessible terms.

---

## Maintenance Agent

**Source:** `src/agents/maintenance/agent.py`

### Purpose

The Maintenance Agent handles appointment scheduling, service history inquiries, and pricing lookups. It uses LangChain's `AgentExecutor` with tool calling, allowing the LLM to autonomously decide which tools to invoke during a conversation turn.

### Configuration

| Parameter     | Value  |
|---------------|--------|
| Temperature   | 0.1    |
| Agent type    | `create_tool_calling_agent` (LangChain) |
| Executor      | `AgentExecutor` with `verbose=True`, `handle_parsing_errors=True` |

### Important Requirement

The Maintenance Agent uses `create_tool_calling_agent`, which requires an LLM that supports **function calling** (tool use). Free-tier models on OpenRouter that lack function calling support will cause this agent to fail. The default model (`meta-llama/llama-3.1-8b-instruct:free`) may or may not support tool calling depending on OpenRouter's current configuration.

### Tools

The agent has access to five tools, all currently returning **mock data**:

#### 1. `check_available_slots`

| Parameter        | Type   | Description                                                    |
|------------------|--------|----------------------------------------------------------------|
| `service_type`   | `str`  | Type of service (`oil_change`, `tire_rotation`, `inspection`, `repair`). |
| `preferred_date` | `str`  | Preferred date in `YYYY-MM-DD` format.                         |

Returns a list of hardcoded time slots (09:00, 11:30, 14:00, 16:30).

#### 2. `book_appointment`

| Parameter        | Type   | Description                                              |
|------------------|--------|----------------------------------------------------------|
| `customer_name`  | `str`  | Customer's full name.                                    |
| `service_type`   | `str`  | Type of service requested.                               |
| `date`           | `str`  | Appointment date (`YYYY-MM-DD`).                         |
| `time`           | `str`  | Appointment time (`HH:MM`).                              |
| `vehicle_info`   | `str`  | Vehicle make/model/year (optional).                      |

Returns a confirmation with a generated number (`APT-{timestamp}`).

#### 3. `get_service_history`

| Parameter      | Type   | Description                         |
|----------------|--------|-------------------------------------|
| `customer_id`  | `str`  | Customer ID or identifier.          |

Returns hardcoded service history entries.

#### 4. `cancel_appointment`

| Parameter              | Type   | Description                              |
|------------------------|--------|------------------------------------------|
| `confirmation_number`  | `str`  | The appointment confirmation number.     |

Returns cancellation confirmation.

#### 5. `get_service_pricing`

| Parameter      | Type   | Description                                |
|----------------|--------|--------------------------------------------|
| `service_type` | `str`  | Type of service to get pricing for.        |

Returns pricing from a hardcoded lookup table:

| Service                | Price Range              |
|------------------------|--------------------------|
| Oil change             | $49.99 -- $79.99         |
| Tire rotation          | $29.99                   |
| Inspection             | $89.99                   |
| Brake service          | $149.99 -- $399.99       |
| Transmission service   | $149.99 -- $249.99       |
| Air filter             | $24.99 -- $49.99         |
| Battery replacement    | $149.99 -- $299.99       |

### System Prompt Behavior

The Maintenance Agent system prompt instructs the LLM to:

1. Always confirm details before booking.
2. Suggest appropriate services based on vehicle history.
3. Be proactive about reminding customers of upcoming maintenance.
4. Ask for vehicle information if not provided.
5. Be friendly and professional.

The prompt includes the current date (injected at runtime via `datetime.now()`).

### Multi-Turn Conversation

The agent maintains chat history by building a `chat_history` list from all previous messages in `state["messages"]` (excluding the latest). This enables multi-turn conversations where the agent can reference earlier exchanges.

### Example Interactions

**User:** "I need to schedule an oil change for next Tuesday."

**Agent behavior:** Calls `check_available_slots(service_type="oil_change", preferred_date="2025-01-14")`, presents available slots, then uses `book_appointment` once the customer confirms a time.

**User:** "How much does a brake service cost?"

**Agent behavior:** Calls `get_service_pricing(service_type="brake_service")` and returns the price range.

---

## Troubleshoot Agent

**Source:** `src/agents/troubleshoot/agent.py`

### Purpose

The Troubleshoot Agent diagnoses vehicle problems by combining diagnostic decision trees with LLM-powered reasoning. It identifies symptoms, asks targeted follow-up questions, assesses severity, and recommends next steps.

### Configuration

| Parameter     | Value  |
|---------------|--------|
| Temperature   | 0.2    |

The slightly higher temperature (compared to 0.1 for other agents) allows for more nuanced diagnostic reasoning.

### Diagnostic Decision Trees

Five built-in decision trees cover common automotive problems:

#### 1. Engine Warning Light (`engine_warning_light`)

**Trigger keywords:** `check engine`, `engine light`, `warning light`, `dashboard light`

| Key Questions | Common Causes |
|---------------|---------------|
| Is the light steady or flashing? | Loose gas cap |
| Any changes in engine performance? | Oxygen sensor issue |
| When did you first notice it? | Catalytic converter problem |
| Recently refueled? | Mass airflow sensor |
| | Spark plugs/ignition coils |

#### 2. Brake Issues (`brake_issues`)

**Trigger keywords:** `brake`, `braking`, `stopping`, `pedal`

| Key Questions | Common Causes |
|---------------|---------------|
| Squealing, grinding, or other noises when braking? | Worn brake pads |
| Brake pedal soft, spongy, or goes to the floor? | Warped brake rotors |
| Vehicle pulls to one side when braking? | Low brake fluid |
| Vibration in steering wheel when braking? | Air in brake lines |
| | Stuck caliper |

#### 3. Starting Problems (`starting_problems`)

**Trigger keywords:** `start`, `starting`, `won't turn on`, `dead`, `click`

| Key Questions | Common Causes |
|---------------|---------------|
| Does the engine crank but not start? | Dead or weak battery |
| Do you hear a clicking sound? | Corroded battery terminals |
| Are dashboard lights dim or flickering? | Faulty starter motor |
| Has the vehicle been sitting unused? | Fuel delivery issue |
| | Ignition switch problem |

#### 4. Overheating (`overheating`)

**Trigger keywords:** `overheat`, `hot`, `temperature`, `steam`, `coolant`

| Key Questions | Common Causes |
|---------------|---------------|
| Is the temperature gauge in the red zone? | Low coolant level |
| See steam or smell coolant? | Thermostat failure |
| Is the AC working properly? | Water pump issue |
| When was coolant last checked/changed? | Radiator blockage |
| | Cooling fan malfunction |

#### 5. Strange Noises (`strange_noises`)

**Trigger keywords:** `noise`, `sound`, `squeal`, `grind`, `rattle`, `clunk`

| Key Questions | Common Causes |
|---------------|---------------|
| Where does the noise come from? | Worn belts |
| When does it occur? | Suspension components |
| How would you describe the sound? | Exhaust system |
| Does it happen at certain speeds? | Wheel bearings |
| | CV joints |

### Keyword Matching

The `_get_diagnostic_context` method performs case-insensitive keyword matching against the user's input. If any keywords match, the corresponding decision tree's questions and common causes are injected into the system prompt. Multiple trees can match simultaneously. If no keywords match, the system prompt includes: `"No specific diagnostic pattern matched. Use general troubleshooting approach."`

### Safety Keyword Detection

After the LLM generates its response, `_check_safety_concerns` scans the **user's original input** for safety-critical keywords. If a match is found, a safety warning is **prepended** to the response:

| Keyword    | Safety Warning |
|------------|----------------|
| `brake`    | Brake issues can be life-threatening. If you're unsure about your brakes, do not drive the vehicle. |
| `steering` | Steering problems are dangerous. Have the vehicle towed if steering feels unsafe. |
| `smoke`    | Smoke can indicate fire risk. Pull over safely and exit the vehicle if you see smoke. |
| `fire`     | If you smell burning or see flames, stop immediately, exit the vehicle, and call emergency services. |
| `airbag`   | Airbag warning lights indicate a serious safety system issue. Get professional inspection immediately. |

### DiagnosticResult Model

The agent defines a Pydantic model for structured diagnostic output (available for programmatic use):

```python
class DiagnosticResult(BaseModel):
    symptoms: list[str]
    possible_causes: list[str]
    recommended_actions: list[str]
    severity: Severity        # LOW, MEDIUM, HIGH, CRITICAL
    requires_professional: bool
    safety_warning: Optional[str]
```

Note: The current `process()` method returns free-text LLM output rather than a structured `DiagnosticResult`. The model is defined but not yet used in the main processing flow.

### System Prompt Behavior

The Troubleshoot Agent system prompt instructs the LLM to:

1. **Safety first** -- Always warn about safety concerns.
2. Ask clarifying questions to narrow down the problem.
3. Explain technical concepts in simple terms.
4. Be clear about what requires professional service vs. DIY fixes.
5. Never encourage unsafe practices.
6. For dangerous problems (brakes, steering, etc.), emphasize getting professional help immediately.

### Example Interactions

**User:** "My car is making a grinding noise when I brake."

**Agent behavior:** Matches `brake_issues` and `strange_noises` trees, injects both into the system prompt, generates a diagnostic response, then prepends a safety warning because "brake" is a safety keyword.

**User:** "My engine won't start, I just hear clicking."

**Agent behavior:** Matches `starting_problems` tree, injects the diagnostic context, and walks the user through common causes (battery, starter motor, etc.).

---

## Human Handoff

**Source:** `src/api/handoff.py`

### Purpose

The `HumanHandoffManager` determines when a conversation should be escalated from automated agents to live human support, and manages the escalation process including optional webhook notification.

### Confidence Threshold

- **Default:** `0.7` (configurable via `CONFIDENCE_THRESHOLD` env var)
- Any classification with a confidence score below this threshold triggers automatic escalation.
- Since the orchestrator assigns `0.85` for successful classification and `0.50` for fallback, a fallback classification will always trigger escalation if the handoff manager is invoked.

### Escalation Reasons

| Reason              | Enum Value          | Trigger                                               |
|---------------------|---------------------|-------------------------------------------------------|
| Low confidence      | `low_confidence`    | `confidence_score < confidence_threshold` (default 0.7) |
| User request        | `user_request`      | User message contains an escalation phrase.           |
| Sensitive topic     | `sensitive_topic`   | User message contains sensitive keywords.             |
| Safety concern      | `safety_concern`    | User message contains safety-critical keywords.       |
| Complex issue       | `complex_issue`     | Programmatically triggered (no automatic detection).  |
| Repeated failure    | `repeated_failure`  | Programmatically triggered (no automatic detection).  |

### User Request Trigger Phrases

The following phrases in the user's message (case-insensitive) trigger a `USER_REQUEST` escalation:

- "speak to human"
- "talk to agent"
- "human support"
- "real person"
- "talk to someone"
- "speak to someone"
- "customer service"
- "representative"

### Sensitive Topic Keywords

These keywords trigger a `SENSITIVE_TOPIC` escalation:

- `accident`, `injury`, `lawsuit`, `legal`, `recall`, `lawyer`, `attorney`, `sue`, `compensation`, `damage claim`

### Safety Concern Keywords

These keywords trigger a `SAFETY_CONCERN` escalation:

- `brakes not working`, `brake failure`, `airbag`, `fuel leak`, `gas leak`, `smoke`, `fire`, `burning smell`, `steering failure`

### Escalation Flow

1. `should_escalate()` evaluates the confidence score and user message.
2. If escalation is warranted, `escalate()` creates an `EscalationRequest` and optionally POSTs it to the configured webhook URL.
3. If the webhook succeeds, the response is parsed into an `EscalationResponse`.
4. If the webhook fails or is not configured, a default `EscalationResponse` is returned with status `"queued"` and estimated wait time of 5 minutes.
5. `get_handoff_response()` formats the escalation response into a user-facing message including wait time, agent name (if assigned), and reference number.

### Pydantic Models

**EscalationRequest:**

| Field                  | Type               | Description                            |
|------------------------|--------------------|----------------------------------------|
| `session_id`           | `str`              | Session identifier.                    |
| `customer_id`          | `Optional[str]`    | Customer identifier.                   |
| `reason`               | `EscalationReason` | Why the escalation was triggered.      |
| `confidence_score`     | `Optional[float]`  | Classification confidence at trigger.  |
| `conversation_summary` | `str`              | Summary of the conversation so far.    |
| `last_user_message`    | `str`              | The message that triggered escalation. |
| `metadata`             | `dict`             | Additional metadata.                   |
| `timestamp`            | `datetime`         | UTC timestamp of the escalation.       |

**EscalationResponse:**

| Field                  | Type               | Description                            |
|------------------------|--------------------|----------------------------------------|
| `escalation_id`        | `str`              | Unique escalation identifier.          |
| `status`               | `str`              | `queued`, `assigned`, `in_progress`, or `resolved`. |
| `estimated_wait_time`  | `Optional[int]`    | Estimated wait in minutes.             |
| `agent_name`           | `Optional[str]`    | Name of the assigned human agent.      |
| `message`              | `str`              | User-facing escalation message.        |

### Escalation Messages by Reason

| Reason              | Message                                                                                              |
|---------------------|------------------------------------------------------------------------------------------------------|
| `low_confidence`    | "I understand your question is complex. I'm transferring you to one of our specialists..."          |
| `user_request`      | "Of course! I'm connecting you to a human representative. Please wait a moment."                    |
| `sensitive_topic`   | "This matter requires special attention from our team. A specialist will contact you shortly."       |
| `complex_issue`     | "Your situation needs a more detailed analysis. I'm connecting you with a specialized technician."  |
| `repeated_failure`  | "I apologize for the difficulty. I'm transferring you to a representative..."                       |
| `safety_concern`    | "Safety concerns are our priority. A specialist will contact you immediately to assist."            |

---

## Configuration

All settings are managed via environment variables (or a `.env` file) through the `Settings` class in `src/api/config.py` (Pydantic `BaseSettings`).

### Environment Variables

#### LLM Provider

| Variable               | Default                                           | Description                          |
|------------------------|---------------------------------------------------|--------------------------------------|
| `OPENROUTER_API_KEY`   | `""` (empty)                                      | API key for OpenRouter.              |
| `OPENROUTER_BASE_URL`  | `https://openrouter.ai/api/v1`                    | OpenRouter API base URL.             |
| `LLM_MODEL`           | `meta-llama/llama-3.1-8b-instruct:free`           | Model identifier on OpenRouter.      |

#### Embeddings

| Variable               | Default                                           | Description                          |
|------------------------|---------------------------------------------------|--------------------------------------|
| `EMBEDDING_MODEL`      | `nomic-ai/nomic-embed-text-v1.5`                  | Embedding model for RAG.             |
| `EMBEDDING_DIMENSION`  | `768`                                             | Embedding vector dimension.          |

#### Database

| Variable               | Default                                           | Description                          |
|------------------------|---------------------------------------------------|--------------------------------------|
| `DATABASE_URL`         | `postgresql://genai:genai_secret@localhost:5432/genai_auto` | PostgreSQL connection string.   |

#### Redis Cache

| Variable               | Default                                           | Description                          |
|------------------------|---------------------------------------------------|--------------------------------------|
| `REDIS_URL`            | `redis://localhost:6379`                           | Redis connection URL.                |
| `CACHE_TTL`            | `3600`                                            | Cache time-to-live in seconds.       |
| `CACHE_ENABLED`        | `true`                                            | Enable/disable caching.              |

#### Application

| Variable               | Default                                           | Description                          |
|------------------------|---------------------------------------------------|--------------------------------------|
| `LOG_LEVEL`            | `INFO`                                            | Logging level.                       |
| `API_HOST`             | `0.0.0.0`                                         | API server bind host.                |
| `API_PORT`             | `8000`                                            | API server bind port.                |
| `DEBUG`                | `false`                                           | Debug mode toggle.                   |

#### Authentication

| Variable                    | Default                                      | Description                          |
|-----------------------------|----------------------------------------------|--------------------------------------|
| `JWT_SECRET_KEY`            | `change-me-in-production-use-openssl-rand-hex-32` | JWT signing secret.             |
| `JWT_ALGORITHM`             | `HS256`                                      | JWT algorithm.                       |
| `JWT_ACCESS_EXPIRE_MINUTES` | `30`                                         | Access token TTL in minutes.         |
| `JWT_REFRESH_EXPIRE_DAYS`   | `7`                                          | Refresh token TTL in days.           |

#### Human Handoff

| Variable                 | Default   | Description                                       |
|--------------------------|-----------|---------------------------------------------------|
| `CONFIDENCE_THRESHOLD`   | `0.7`     | Confidence below this triggers escalation.         |
| `HUMAN_SUPPORT_WEBHOOK`  | `""`      | Webhook URL to notify human support system.        |

#### Scheduler

| Variable               | Default                     | Description                          |
|------------------------|-----------------------------|--------------------------------------|
| `SCHEDULER_API_URL`    | `http://localhost:9000`     | External scheduler API URL.          |
| `SCHEDULER_API_KEY`    | `""`                        | Scheduler API authentication key.    |

#### Observability

| Variable                | Default   | Description                                  |
|-------------------------|-----------|----------------------------------------------|
| `LANGCHAIN_TRACING_V2`  | `false`  | Enable LangSmith tracing.                    |
| `LANGCHAIN_API_KEY`     | `""`     | LangSmith API key.                           |

#### Privacy

| Variable   | Default | Description                          |
|------------|---------|--------------------------------------|
| `MASK_PII` | `true`  | Mask personally identifiable information in logs. |

### Model Selection Guide

The `LLM_MODEL` environment variable controls which model all three agents and the orchestrator use. When selecting a model, consider the following:

| Requirement                  | Recommendation                                        |
|------------------------------|-------------------------------------------------------|
| Free tier, basic usage       | `meta-llama/llama-3.1-8b-instruct:free` (default)    |
| Maintenance Agent tool use   | A model with function calling support (e.g., `openai/gpt-4o-mini`, `anthropic/claude-3.5-sonnet`) |
| Higher quality responses     | Larger parameter models or commercial models via OpenRouter |

---

## Known Limitations

### 1. Mock Tool Implementations

All five Maintenance Agent tools (`check_available_slots`, `book_appointment`, `get_service_history`, `cancel_appointment`, `get_service_pricing`) return **hardcoded mock data**. Each tool has a `# TODO` comment indicating where real API/database integration should be added. No actual appointments are booked, no real service history is retrieved, and no real scheduling system is consulted.

### 2. Function Calling Model Requirement

The Maintenance Agent uses `create_tool_calling_agent` from LangChain, which requires the LLM to support function calling (tool use). The default free model (`meta-llama/llama-3.1-8b-instruct:free`) may not support this feature, causing the Maintenance Agent to fail with parsing errors. Switching to a model with function calling support (such as GPT-4o-mini or Claude 3.5 Sonnet via OpenRouter) resolves this.

### 3. Single Model for All Agents

All agents and the orchestrator share the same `LLM_MODEL` configuration. There is no per-agent model override. This means you cannot, for example, use a free model for the Specs Agent while using a function-calling model for the Maintenance Agent.

### 4. DiagnosticResult Not Used in Flow

The `DiagnosticResult` Pydantic model is defined in the Troubleshoot Agent but is not currently used by the `process()` method. The agent returns free-text LLM output instead of structured diagnostic data. The model exists for future structured output integration.

### 5. Safety Keyword Detection is Simple Substring Matching

Both the Troubleshoot Agent's `_check_safety_concerns` and the Human Handoff's keyword detection use basic `in` substring matching. This can produce false positives (e.g., "firewall" triggering the "fire" safety warning) and false negatives (e.g., misspelled keywords or synonyms being missed).

### 6. No Persistent Conversation State

While the orchestrator passes `session_id` through the state, conversation history is managed in-memory within a single request. There is no built-in persistence layer for multi-request conversation continuity at the orchestrator level -- the caller is responsible for maintaining and re-supplying `messages` across requests.

### 7. Confidence Scoring is Binary

The orchestrator assigns only two confidence values: `0.85` for a successfully classified intent and `0.50` for the fallback case. There is no granular confidence estimation based on the LLM's actual certainty or token probabilities.

### 8. No Webhook Integration Configured by Default

The `HUMAN_SUPPORT_WEBHOOK` defaults to an empty string, meaning escalation requests are not forwarded to any external system by default. The handoff manager returns a default queued response without actually notifying any human support team.
