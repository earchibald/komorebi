"""Komorebi Backend - Main FastAPI Application.

A cognitive infrastructure service providing:
- Fast chunk capture and processing
- Recursive summarization and context management
- MCP server aggregation
- Real-time SSE streaming
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import chunks_router, projects_router, mcp_router, sse_router, entities_router
from .db import init_db

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    # Startup
    await init_db()

    # Load MCP servers from config (non-blocking – failures logged, not raised)
    try:
        from pathlib import Path
        from .mcp.config import load_and_register_servers
        from .mcp import mcp_registry as _reg

        connected = await load_and_register_servers(_reg, Path("config/mcp_servers.json"))
        logging.getLogger(__name__).info(f"MCP startup: {connected} server(s) connected")
    except Exception as exc:
        logging.getLogger(__name__).warning(f"MCP startup skipped: {exc}")

    yield

    # Shutdown
    from .mcp import mcp_registry
    await mcp_registry.disconnect_all()


app = FastAPI(
    title="Komorebi",
    description="Cognitive infrastructure for capture, compaction, and context management",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS configuration for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chunks_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(mcp_router, prefix="/api/v1")
app.include_router(sse_router, prefix="/api/v1")
app.include_router(entities_router, prefix="/api/v1")


@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "name": "Komorebi",
        "version": "0.1.0",
        "description": "Cognitive infrastructure service",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
