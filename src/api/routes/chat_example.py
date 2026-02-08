"""
Example chat endpoint with integrated metrics tracking.

This is a REFERENCE implementation showing how to integrate metrics
into your actual chat endpoint.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import time
from ..metrics import track_llm_call, track_llm_error, track_endpoint_metrics


router = APIRouter(prefix="/api/v1", tags=["chat"])


# ============================================================================
# MODELS
# ============================================================================

class ChatRequest(BaseModel):
    message: str
    session_id: str | None = None


class ChatResponse(BaseModel):
    message: str
    agent: str
    session_id: str
    metadata: dict


# ============================================================================
# ENDPOINT WITH METRICS TRACKING
# ============================================================================

@router.post("/chat", response_model=ChatResponse)
@track_endpoint_metrics('chat')  # Automatic latency + in-progress tracking
async def chat(request: ChatRequest):
    """
    Chat endpoint with integrated metrics tracking.
    
    This example shows how to:
    1. Track LLM token usage
    2. Track LLM costs
    3. Track LLM latency
    4. Track LLM errors
    """
    
    try:
        # ====================================================================
        # SIMULATE LLM CALL (replace with actual LangGraph orchestrator)
        # ====================================================================
        
        start_time = time.time()
        
        # Simulated LLM call
        model = "meta-llama/llama-3.1-8b-instruct:free"
        agent = "specs"  # or "maintenance" or "troubleshoot"
        
        # TODO: Replace with actual LangGraph orchestrator call
        # result = await orchestrator.run(request.message)
        
        # Simulated response
        response_text = "This is a simulated response. Replace with actual LLM call."
        input_tokens = len(request.message.split()) * 1.3  # Rough estimate
        output_tokens = len(response_text.split()) * 1.3
        
        # Simulate processing time
        # time.sleep(0.5)  # Remove in production
        
        llm_duration = time.time() - start_time
        
        # ====================================================================
        # TRACK METRICS
        # ====================================================================
        
        track_llm_call(
            model=model,
            agent=agent,
            input_tokens=int(input_tokens),
            output_tokens=int(output_tokens),
            duration=llm_duration
        )
        
        # ====================================================================
        # RETURN RESPONSE
        # ====================================================================
        
        return ChatResponse(
            message=response_text,
            agent=agent,
            session_id=request.session_id or "new_session",
            metadata={
                "model": model,
                "input_tokens": int(input_tokens),
                "output_tokens": int(output_tokens),
                "duration_seconds": round(llm_duration, 3)
            }
        )
    
    except Exception:
        # Track timeout errors
        track_llm_error(error_type='timeout', model=model)
        raise HTTPException(status_code=504, detail="LLM request timed out")
    
    except Exception as e:
        # Track general errors
        track_llm_error(error_type='api_error', model=model)
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")


# ============================================================================
# INTEGRATION GUIDE
# ============================================================================

"""
HOW TO INTEGRATE INTO YOUR ACTUAL CHAT ENDPOINT:

1. Import metrics functions:
   from ..metrics import track_llm_call, track_llm_error, track_endpoint_metrics

2. Add decorator to endpoint:
   @track_endpoint_metrics('chat')
   async def your_chat_endpoint():
       ...

3. After LLM call, track metrics:
   track_llm_call(
       model="your-model",
       agent="specs",  # or which agent was used
       input_tokens=result.usage.input_tokens,
       output_tokens=result.usage.output_tokens,
       duration=elapsed_time
   )

4. In error handlers, track errors:
   track_llm_error(error_type='timeout', model='your-model')

5. Token counts:
   - If your LLM provider returns token counts, use those
   - If not, estimate: tokens ≈ words * 1.3 (rough approximation)
   - For accurate tracking, use tiktoken library:
     
     import tiktoken
     enc = tiktoken.encoding_for_model("gpt-3.5-turbo")
     tokens = len(enc.encode(text))

That's it! Metrics will be automatically collected and exposed at /api/v1/metrics
"""
