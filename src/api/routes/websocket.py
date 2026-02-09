"""
WebSocket routes for real-time chat streaming.

Provides streaming chat responses with:
- Authentication via query param or initial message
- Real-time token streaming from LLM
- Progress updates (RAG retrieval, agent routing)
- Error handling and reconnection support
"""

from typing import Dict, Any, Optional
from datetime import datetime

import structlog
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth.jwt_auth import decode_token, AuthenticatedUser
from src.api.config import get_settings
from src.storage.database import get_db
from src.orchestrator.graph import create_workflow, AgentState

logger = structlog.get_logger()
settings = get_settings()

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manage WebSocket connections."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, client_id: str):
        """Accept and store connection."""
        await websocket.accept()
        self.active_connections[client_id] = websocket
        logger.info("WebSocket connected", client_id=client_id)
    
    def disconnect(self, client_id: str):
        """Remove connection."""
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            logger.info("WebSocket disconnected", client_id=client_id)
    
    async def send_json(self, client_id: str, data: Dict[str, Any]):
        """Send JSON message to client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_json(data)
    
    async def send_text(self, client_id: str, message: str):
        """Send text message to client."""
        if client_id in self.active_connections:
            await self.active_connections[client_id].send_text(message)


manager = ConnectionManager()


async def authenticate_websocket(token: Optional[str]) -> Optional[AuthenticatedUser]:
    """
    Authenticate WebSocket connection.
    
    Args:
        token: JWT token from query param or message
        
    Returns:
        AuthenticatedUser if valid, None otherwise
    """
    if not token:
        return None
    
    try:
        # Remove "Bearer " prefix if present
        if token.startswith("Bearer "):
            token = token[7:]
        
        payload = decode_token(token)
        return AuthenticatedUser(
            user_id=payload["sub"],
            email=payload["email"],
            name=payload["name"]
        )
    except Exception as e:
        logger.warning("WebSocket auth failed", error=str(e))
        return None


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """
    WebSocket endpoint for streaming chat (PoC - No authentication required).
    
    Protocol:
    
    Client → Server (message):
    {
        "type": "message",
        "message": "User question here",
        "session_id": "optional-session-id",
        "customer_id": "optional-customer-id"
    }
    
    Server → Client (progress updates):
    {
        "type": "progress",
        "step": "rag_retrieval" | "agent_routing" | "generating",
        "message": "Human-readable progress message"
    }
    
    Server → Client (streaming tokens):
    {
        "type": "token",
        "token": "word or phrase",
        "partial_response": "accumulated response so far"
    }
    
    Server → Client (complete response):
    {
        "type": "complete",
        "response": "full response text",
        "session_id": "session-id",
        "metadata": {
            "agent": "specs",
            "confidence": 0.95,
            "sources": [...]
        }
    }
    
    Server → Client (error):
    {
        "type": "error",
        "error": "error message",
        "code": "error_code"
    }
    """
    client_id = f"ws_{datetime.utcnow().timestamp()}"
    
    await manager.connect(websocket, client_id)
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message_type = data.get("type")
            
            # Handle messages (no authentication required for PoC)
            if message_type == "message":
                # Extract message data
                user_message = data.get("message", "")
                session_id = data.get("session_id")
                customer_id = data.get("customer_id")
                
                if not user_message:
                    await manager.send_json(client_id, {
                        "type": "error",
                        "error": "Message is required",
                        "code": "EMPTY_MESSAGE"
                    })
                    continue
                
                logger.info(
                    "WebSocket message received",
                    client_id=client_id,
                    message_length=len(user_message),
                    session_id=session_id
                )
                
                try:
                    # Send progress: Starting
                    await manager.send_json(client_id, {
                        "type": "progress",
                        "step": "starting",
                        "message": "Processing your question..."
                    })
                    
                    # Create workflow
                    workflow = create_workflow()
                    
                    # Send progress: Agent routing
                    await manager.send_json(client_id, {
                        "type": "progress",
                        "step": "agent_routing",
                        "message": "Routing to the right expert..."
                    })
                    
                    # Initialize state
                    initial_state: AgentState = {
                        "messages": [{"role": "user", "content": user_message}],
                        "session_id": session_id or f"session-{client_id}",
                        "customer_id": customer_id,
                        "vehicle_id": None,
                        "metadata": {},
                        "current_agent": None,
                        "context": {}
                    }
                    
                    # Send progress: RAG retrieval
                    await manager.send_json(client_id, {
                        "type": "progress",
                        "step": "rag_retrieval",
                        "message": "Searching knowledge base..."
                    })
                    
                    # Run workflow and collect final state
                    final_state = None
                    async for chunk in workflow.astream(initial_state):
                        final_state = chunk
                    
                    # Extract response from final state messages
                    response_text = ""
                    if final_state and "messages" in final_state:
                        # Get last assistant message
                        for msg in reversed(final_state["messages"]):
                            if isinstance(msg, dict) and msg.get("role") == "assistant":
                                response_text = msg.get("content", "")
                                break
                    
                    # Send complete message
                    await manager.send_json(client_id, {
                        "type": "complete",
                        "response": response_text,
                        "session_id": final_state.get("session_id") if final_state else session_id,
                        "metadata": {
                            "agent": final_state.get("current_agent") if final_state else None,
                            "confidence": final_state.get("context", {}).get("confidence", 0.0) if final_state else 0.0,
                            "context": final_state.get("context", {}) if final_state else {}
                        }
                    })
                    
                    logger.info(
                        "WebSocket response sent",
                        client_id=client_id,
                        response_length=len(response_text),
                        agent=final_state.get("current_agent") if final_state else None
                    )
                
                except Exception as e:
                    logger.error(
                        "WebSocket message processing failed",
                        client_id=client_id,
                        error=str(e),
                        exc_info=True
                    )
                    
                    await manager.send_json(client_id, {
                        "type": "error",
                        "error": str(e),
                        "code": "PROCESSING_ERROR"
                    })
    
    except WebSocketDisconnect:
        manager.disconnect(client_id)
        logger.info("WebSocket client disconnected", client_id=client_id)
    
    except Exception as e:
        logger.error(
            "WebSocket error",
            client_id=client_id,
            error=str(e),
            exc_info=True
        )
        manager.disconnect(client_id)


@router.get("/ws/test", response_class=HTMLResponse)
async def websocket_test_page():
    """
    Simple HTML page to test WebSocket chat.
    
    Access at: http://localhost:8000/ws/test
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WebSocket Chat Test</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
            }
            #chat {
                border: 1px solid #ccc;
                height: 400px;
                overflow-y: scroll;
                padding: 10px;
                margin-bottom: 10px;
                background: #f9f9f9;
            }
            .message {
                margin: 5px 0;
                padding: 5px;
            }
            .user {
                color: blue;
                font-weight: bold;
            }
            .assistant {
                color: green;
            }
            .progress {
                color: orange;
                font-style: italic;
            }
            .error {
                color: red;
            }
            input, button {
                padding: 10px;
                font-size: 16px;
            }
            #message {
                width: 70%;
            }
            #send {
                width: 15%;
            }
            #auth {
                margin-bottom: 20px;
            }
        </style>
    </head>
    <body>
        <h1>WebSocket Chat Test</h1>
        
        <div id="auth">
            <input type="text" id="token" placeholder="JWT Token (optional)" style="width: 80%;">
            <button onclick="authenticate()">Authenticate</button>
        </div>
        
        <div id="chat"></div>
        
        <div>
            <input type="text" id="message" placeholder="Type your message..." onkeypress="handleKeyPress(event)">
            <button id="send" onclick="sendMessage()">Send</button>
            <button onclick="clearChat()">Clear</button>
        </div>
        
        <div style="margin-top: 20px;">
            <strong>Status:</strong> <span id="status">Disconnected</span>
        </div>
        
        <script>
            let ws = null;
            let authenticated = false;
            
            function connect() {
                const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
                const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
                
                ws = new WebSocket(wsUrl);
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = 'Connected';
                    document.getElementById('status').style.color = 'green';
                    addMessage('system', 'Connected to WebSocket');
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    handleMessage(data);
                };
                
                ws.onclose = () => {
                    document.getElementById('status').textContent = 'Disconnected';
                    document.getElementById('status').style.color = 'red';
                    addMessage('system', 'Disconnected from WebSocket');
                    authenticated = false;
                };
                
                ws.onerror = (error) => {
                    addMessage('error', 'WebSocket error: ' + error);
                };
            }
            
            function authenticate() {
                const token = document.getElementById('token').value;
                if (!token) {
                    alert('Please enter a token');
                    return;
                }
                
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    connect();
                    setTimeout(() => {
                        ws.send(JSON.stringify({
                            type: 'auth',
                            token: token
                        }));
                    }, 500);
                } else {
                    ws.send(JSON.stringify({
                        type: 'auth',
                        token: token
                    }));
                }
            }
            
            function sendMessage() {
                const input = document.getElementById('message');
                const message = input.value.trim();
                
                if (!message) return;
                
                if (!ws || ws.readyState !== WebSocket.OPEN) {
                    connect();
                    setTimeout(() => sendMessageInternal(message), 500);
                } else {
                    sendMessageInternal(message);
                }
                
                input.value = '';
            }
            
            function sendMessageInternal(message) {
                addMessage('user', message);
                
                ws.send(JSON.stringify({
                    type: 'message',
                    message: message,
                    session_id: 'test-session-' + Date.now()
                }));
            }
            
            function handleMessage(data) {
                switch (data.type) {
                    case 'auth_success':
                        authenticated = true;
                        addMessage('system', '✅ ' + data.message);
                        break;
                    
                    case 'auth_error':
                        addMessage('error', '❌ ' + data.message);
                        break;
                    
                    case 'progress':
                        addMessage('progress', '⏳ ' + data.message);
                        break;
                    
                    case 'token':
                        appendToken(data.token);
                        break;
                    
                    case 'complete':
                        finalizeResponse(data.response, data.metadata);
                        break;
                    
                    case 'error':
                        addMessage('error', '❌ Error: ' + data.error);
                        break;
                }
            }
            
            let currentResponse = null;
            
            function appendToken(token) {
                if (!currentResponse) {
                    currentResponse = document.createElement('div');
                    currentResponse.className = 'message assistant';
                    document.getElementById('chat').appendChild(currentResponse);
                }
                currentResponse.textContent += token;
                scrollToBottom();
            }
            
            function finalizeResponse(response, metadata) {
                if (currentResponse) {
                    currentResponse.textContent = response;
                    if (metadata && metadata.agent) {
                        currentResponse.textContent += ` [${metadata.agent}]`;
                    }
                } else {
                    addMessage('assistant', response);
                }
                currentResponse = null;
                scrollToBottom();
            }
            
            function addMessage(type, text) {
                const chat = document.getElementById('chat');
                const msg = document.createElement('div');
                msg.className = 'message ' + type;
                msg.textContent = text;
                chat.appendChild(msg);
                scrollToBottom();
            }
            
            function scrollToBottom() {
                const chat = document.getElementById('chat');
                chat.scrollTop = chat.scrollHeight;
            }
            
            function clearChat() {
                document.getElementById('chat').innerHTML = '';
                currentResponse = null;
            }
            
            function handleKeyPress(event) {
                if (event.key === 'Enter') {
                    sendMessage();
                }
            }
            
            // Connect on page load
            connect();
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html)
