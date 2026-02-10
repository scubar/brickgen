"""Main FastAPI application."""
import asyncio
import logging
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
from backend.database import init_db
from backend.api.routes import search, generate, download, settings as settings_routes, projects, parts
from backend.version import __version__

# Configure logging (level from settings.log_level / LOG_LEVEL env)
_log_level = getattr(logging, str(settings.log_level).upper(), logging.INFO)
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize database
init_db()

# Create FastAPI app
app = FastAPI(
    title="BrickGen API",
    description="LEGO set 3D printing file generator",
    version=__version__
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(search.router, prefix=settings.api_prefix, tags=["search"])
app.include_router(generate.router, prefix=settings.api_prefix, tags=["generate"])
app.include_router(download.router, prefix=settings.api_prefix, tags=["download"])
app.include_router(settings_routes.router, prefix=settings.api_prefix, tags=["settings"])
app.include_router(projects.router, prefix=settings.api_prefix, tags=["projects"])
app.include_router(parts.router, prefix=settings.api_prefix, tags=["parts"])

@app.on_event("startup")
async def startup_event():
    """Start the WebSocket progress broadcast task (drains queue from worker thread)."""
    asyncio.create_task(generate.broadcast_progress_task())

@app.get(f"{settings.api_prefix}/version")
async def get_version():
    """Return current BrickGen version (for job version comparison)."""
    return {"version": __version__}


@app.get("/health")
async def health_check():
    """Health check endpoint for Kubernetes."""
    from backend.api.integrations.ldraw import LDrawManager
    
    # Check if LDraw library exists
    ldraw_manager = LDrawManager()
    ldraw_stats = ldraw_manager.get_library_stats()
    
    return {
        "status": "healthy",
        "ldraw_library": ldraw_stats
    }


# Mount static files for frontend (will be added in Docker build)
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    # Mount static assets directory if it exists
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
        logger.info("Serving static assets from /assets")
    
    # Serve root-level static files (favicon, etc.)
    @app.get("/favicon.ico")
    async def favicon():
        favicon_path = static_dir / "favicon.ico"
        if favicon_path.exists():
            return FileResponse(str(favicon_path))
        return {"detail": "Not Found"}
    
    # Catch-all route for SPA - must be last!
    # This handles client-side routing by serving index.html for all non-API routes
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        """Serve index.html for all non-API routes to support client-side routing."""
        # Serve index.html for all routes (let React Router handle routing)
        index_path = static_dir / "index.html"
        if index_path.exists():
            return FileResponse(str(index_path))
        else:
            return {"message": "Frontend not found"}
else:
    logger.warning("Static directory not found - frontend not available")
    
    @app.get("/")
    async def root():
        return {
            "message": "BrickGen API",
            "docs": "/docs",
            "health": "/health"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
