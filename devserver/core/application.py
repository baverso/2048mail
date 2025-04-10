import uvicorn
import logging
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from devserver.core.config import settings
from devserver.api import (
    ui_router, 
    auth_router, 
    email_router, 
    websocket_router, 
    debug_router
)
from devserver.websockets.connection_manager import connection_manager
from devserver.services.feedback_service import feedback_service

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        FastAPI application instance
    """
    # Initialize FastAPI app
    app = FastAPI(title="Quillo Email Management System")
    
    # Add session middleware
    app.add_middleware(SessionMiddleware, secret_key=settings.SESSION_SECRET_KEY)
    
    # Register the connection manager with the feedback service
    feedback_service.set_connection_manager(connection_manager)
    
    # Include routers
    app.include_router(ui_router.router)
    app.include_router(auth_router.router)
    app.include_router(email_router.router)
    app.include_router(websocket_router.router)
    app.include_router(debug_router.router)
    
    # Optional: Add static files mount if needed
    # app.mount("/static", StaticFiles(directory="static"), name="static")
    
    return app


# Create an app instance for direct usage with uvicorn
app = create_app()


def run_server():
    """Run the server with the configured settings."""
    uvicorn.run(
        app, 
        host=settings.HOST, 
        port=settings.PORT, 
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL,
        access_log=settings.ACCESS_LOG
    ) 


if __name__ == "__main__":
    run_server() 