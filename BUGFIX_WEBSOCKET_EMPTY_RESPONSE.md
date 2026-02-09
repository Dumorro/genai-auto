# Bug Fix: WebSocket Empty Response

## Issue
Chat interface was showing empty responses from the AI agents. The WebSocket received the complete message event, but the `response` field was always empty (`""`).

**Symptoms:**
- WebSocket connection successful
- Progress messages working correctly
- Final response arrives but with empty content
- Console shows: `{response: "", metadata: {...}, hasCurrentDiv: false}`

## Root Cause
The bug was in `src/api/routes/websocket.py` in the message processing handler.

**Original code:**
```python
# Run workflow and collect final state
final_state = None
async for chunk in workflow.astream(initial_state):
    final_state = chunk
```

**Problem:**
- `workflow.astream()` returns **partial chunks** (one per node in the LangGraph)
- Each chunk contains only the state **changes** from that specific node
- By assigning `final_state = chunk`, we only kept the **last chunk**
- The last chunk might not contain the assistant's message if it was added in an earlier node

## Solution
Changed from `astream()` to `ainvoke()` to get the complete final state:

```python
# Run workflow and get final state
final_state = await workflow.ainvoke(initial_state)

logger.info(
    "Workflow completed",
    client_id=client_id,
    final_state_keys=list(final_state.keys()) if final_state else [],
    messages_count=len(final_state.get("messages", [])) if final_state else 0
)
```

**Why this works:**
- `ainvoke()` returns the **complete final state** after all nodes execute
- All messages (user + assistant) are present in `final_state["messages"]`
- The extraction logic can now find the assistant's response correctly

## Files Changed
- `src/api/routes/websocket.py` - Line ~216-222

## Testing
After the fix:
1. Send message via chat interface
2. Response now appears correctly in the chat
3. Agent routing, RAG retrieval, and response generation all working

## Deployment
Container rebuild required:
```bash
docker-compose build api
docker-compose up -d api
```

## Credits
- Bug discovered: 2026-02-09
- Fixed by: Jarvison (AI Assistant)
- Reported by: Dumorro
