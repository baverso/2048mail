import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from devserver.services.oauth_service import (
    OAuthServiceInterface, 
    get_oauth_service,
    is_authenticated
)
from devserver.services.user_state_service import user_state_service
from devserver.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

# Create templates instance
templates = Jinja2Templates(directory=settings.TEMPLATES_DIR)


@router.get("/", response_class=HTMLResponse)
async def index(
    request: Request,
    authenticated: bool = Depends(is_authenticated),
    oauth_service: OAuthServiceInterface = Depends(get_oauth_service)
):
    """
    Main page that shows authentication status and email processing options.
    """
    # Get or create user ID
    user_id = await user_state_service.get_current_user_id(request)
    user_state = user_state_service.get_user_state(user_id)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "is_authenticated": authenticated,
        "status": user_state.background_task.status,
        "user_id": user_id
    }) 