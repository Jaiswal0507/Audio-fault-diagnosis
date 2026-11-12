"""FastAPI Application Entry Point for MachineSense.

This module initializes the FastAPI service, configures CORS middleware,
and mounts API routers for machine condition diagnosis, history telemetry,
and multi-tenant JWT authentication.
"""

import os
from pathlib import Path
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Ensure project root and backend directory are available for imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from backend.app.api.analysis import router as analysis_router
    from backend.app.api.history import router as history_router
    from backend.app.api.auth import router as auth_router
    from backend.app.database.database import init_db
except ImportError:
    try:
        from app.api.analysis import router as analysis_router
        from app.api.history import router as history_router
        from app.api.auth import router as auth_router
        from app.database.database import init_db
    except ImportError:
        from .api.analysis import router as analysis_router
        from .api.history import router as history_router
        from .api.auth import router as auth_router
        from .database.database import init_db

# Initialize FastAPI application
app = FastAPI(
    title="MachineSense API",
    version="1.0.0",
    description="Web-Based Acoustic Machine Condition Monitoring & Fault Diagnosis Platform with Multi-Tenant JWT Auth",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS Middleware using ALLOWED_ORIGINS environment variable
raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://localhost:3000")
allowed_origins = [origin.strip() for origin in raw_origins.split(",") if origin.strip()]
if not allowed_origins:
    allowed_origins = ["http://localhost:5173", "http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-initialize database tables on server startup
@app.on_event("startup")
def on_startup():
    init_db()

# Mount API routers
app.include_router(auth_router, prefix="/api/v1/auth")
# Also mount at /api/v1 for direct convenience routing (/api/v1/login, /api/v1/register)
app.include_router(auth_router, prefix="/api/v1", include_in_schema=False)
app.include_router(analysis_router, prefix="/api/v1")
app.include_router(history_router, prefix="/api/v1")


@app.get("/api/v1/health", tags=["Health"])
def health_check():
    """Health check endpoint to verify backend service status."""
    return {"status": "MachineSense API is running"}


@app.get("/", tags=["Root"])
def root():
    """Root endpoint providing service metadata."""
    return {
        "service": "MachineSense API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)
