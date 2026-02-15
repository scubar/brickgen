"""Main FastAPI application."""
import asyncio
import logging
import sys
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from backend.config import settings
from backend.database import init_db
from backend.api.routes import search, generate, download, settings as settings_routes, projects, parts, auth
from backend.core.job_progress import broadcast_progress_task
from backend.auth import get_current_user
from backend.version import __version__

# Configure logging (level from settings.log_level / LOG_LEVEL env)
_log_level = getattr(logging, str(settings.log_level).upper(), logging.INFO)
logging.basicConfig(
    level=_log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Validate authentication credentials are configured
def validate_auth_credentials():
    """Ensure authentication credentials are not using default insecure values."""
    insecure_usernames = ["admin"]
    insecure_passwords = ["changeme"]
    insecure_jwt_secrets = [
        "dev_secret_key_change_in_production",
        "your_secret_key_here_change_in_production"
    ]
    
    errors = []
    
    if settings.auth_username in insecure_usernames:
        errors.append(
            f"AUTH_USERNAME is set to default value '{settings.auth_username}'. "
            "Please set a custom username in your .env file."
        )
    
    if settings.auth_password in insecure_passwords:
        errors.append(
            f"AUTH_PASSWORD is set to default value '{settings.auth_password}'. "
            "Please set a secure password in your .env file."
        )
    
    if settings.jwt_secret_key in insecure_jwt_secrets:
        errors.append(
            "JWT_SECRET_KEY is set to a default value. "
            "Please generate a secure secret key (e.g., using 'openssl rand -hex 32') "
            "and set it in your .env file."
        )
    
    if errors:
        error_msg = "\n\n" + "=" * 80 + "\n"
        error_msg += "SECURITY ERROR: Insecure authentication configuration detected!\n"
        error_msg += "=" * 80 + "\n\n"
        for error in errors:
            error_msg += f"  • {error}\n"
        error_msg += "\n"
        error_msg += "Application startup aborted. Please fix your .env file with secure values.\n"
        error_msg += "After fixing, restart the container with: docker-compose up -d\n"
        error_msg += "=" * 80 + "\n"
        
        # Use logger.critical for fatal errors
        logger.critical(error_msg)
        
        # Exit with code 1 to indicate configuration error
        # Container will NOT automatically restart (restart policy is "no")
        sys.exit(1)

# Validate credentials before initializing anything
validate_auth_credentials()

# Task reference for the WebSocket broadcast task
_broadcast_task = None

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
# Auth routes (no authentication required for login)
app.include_router(auth.router, prefix=settings.api_prefix, tags=["auth"])

# Protected API routes (authentication applied at route level to exclude WebSocket routes)
app.include_router(search.router, prefix=settings.api_prefix, tags=["search"])
app.include_router(generate.router, prefix=settings.api_prefix, tags=["generate"])
app.include_router(download.router, prefix=settings.api_prefix, tags=["download"])
app.include_router(settings_routes.router, prefix=settings.api_prefix, tags=["settings"])
app.include_router(projects.router, prefix=settings.api_prefix, tags=["projects"])
app.include_router(parts.router, prefix=settings.api_prefix, tags=["parts"])

@app.on_event("startup")
async def startup_event():
    """Start the WebSocket progress broadcast task (drains queue from worker thread)."""
    global _broadcast_task
    _broadcast_task = asyncio.create_task(broadcast_progress_task())
    
    def task_done_callback(task):
        """Log if the broadcast task terminates unexpectedly."""
        try:
            task.result()
        except asyncio.CancelledError:
            logger.info("WebSocket broadcast task was cancelled")
        except Exception as e:
            logger.error(f"WebSocket broadcast task failed with exception: {e}", exc_info=True)
    
    _broadcast_task.add_done_callback(task_done_callback)

@app.on_event("shutdown")
async def shutdown_event():
    """Gracefully cancel the WebSocket broadcast task on shutdown."""
    global _broadcast_task
    if _broadcast_task and not _broadcast_task.done():
        _broadcast_task.cancel()
        try:
            await _broadcast_task
        except asyncio.CancelledError:
            pass

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
