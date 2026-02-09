"""FastAPI application entry point."""

import structlog
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, RedirectResponse

from src.api.config import get_settings
from src.api.routes import auth, chat, health, documents, metrics as metrics_routes, evaluation, websocket
from src.api.observability import RequestTracingMiddleware
from src.api.cache import close_redis
from src.storage.database import init_db

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
)

logger = structlog.get_logger()
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info(
        "Starting GenAI Auto API",
        version="1.0.0",
        llm_model=settings.llm_model,
        cache_enabled=settings.cache_enabled,
    )
    await init_db()
    yield
    logger.info("Shutting down GenAI Auto API")
    await close_redis()


app = FastAPI(
    title="GenAI Auto API",
    description="Multi-agent AI system for automotive customer service",
    version="1.0.0",
    lifespan=lifespan,
)

# Request tracing middleware (must be first)
app.add_middleware(RequestTracingMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/v1", tags=["Auth"])
app.include_router(chat.router, prefix="/api/v1", tags=["Chat"])
app.include_router(documents.router, prefix="/api/v1", tags=["Documents"])
app.include_router(metrics_routes.router, prefix="/api/v1", tags=["Metrics"])
app.include_router(evaluation.router, prefix="/api/v1", tags=["Evaluation"])
app.include_router(websocket.router)  # No prefix for WebSocket


# Serve frontend static files
FRONTEND_DIR = Path(__file__).parent.parent.parent / "frontend"
if FRONTEND_DIR.exists():
    # Redirect root to chat (PoC - no home page needed)
    @app.get("/")
    async def serve_home():
        """Redirect to chat interface."""
        return RedirectResponse(url="/chat")
    
    # Serve chat.html
    @app.get("/chat")
    async def serve_chat():
        """Serve the chat page."""
        return FileResponse(FRONTEND_DIR / "chat.html")
    
    # Mount static files (for any additional assets)
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")
else:
    # Fallback if frontend not found
    @app.get("/")
    async def root():
        """API root endpoint."""
        return {
            "name": "GenAI Auto API",
            "version": "1.0.0",
            "description": "Multi-agent AI system for automotive customer service",
            "docs": "/docs",
            "frontend": "Not found (run from project root or mount /frontend)",
            "features": {
                "authentication": "JWT (built-in)",
                "caching": settings.cache_enabled,
                "pii_protection": settings.mask_pii,
                "human_handoff": bool(settings.human_support_webhook),
            },
        }
