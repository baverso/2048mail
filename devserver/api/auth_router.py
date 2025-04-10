import logging
from fastapi import APIRouter, Request, Depends
from fastapi.responses import RedirectResponse

from devserver.services.oauth_service import (
    OAuthServiceInterface, 
    get_oauth_service,
    get_user_email
)
from devserver.services.user_state_service import user_state_service

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/login")
async def login(oauth_service: OAuthServiceInterface = Depends(get_oauth_service)):
    """
    Start the OAuth flow by redirecting to Google's auth page.
    """
    # Check if we already have valid credentials
    creds = oauth_service.get_credentials()
    if creds and creds.valid:
        return RedirectResponse(url="/?status=already_authenticated")
    
    # Get authorization URL and state
    auth_url, state, flow = oauth_service.get_authorization_url()
    
    # Store the flow state in a cookie or session
    response = RedirectResponse(url=auth_url)
    response.set_cookie(key="flow_state", value=state)
    
    return response


@router.get("/oauth2callback")
async def oauth2callback(
    request: Request, 
    oauth_service: OAuthServiceInterface = Depends(get_oauth_service)
):
    """
    Handle the OAuth callback from Google.
    """
    try:
        logger.info("Received callback at /oauth2callback")
        logger.info(f"Request URL: {request.url}")
        
        # Check if there's an error in the callback
        if request.query_params.get('error'):
            error = request.query_params.get('error')
            logger.error(f"OAuth error: {error}")
            return f"Authentication failed: {error}"
        
        # Recreate the flow with the same redirect URI
        flow = oauth_service.create_authorization_flow()
        
        # Exchange the authorization code for credentials
        creds = oauth_service.fetch_token_from_response(flow, str(request.url))
        
        # Update user ID with email if available
        if hasattr(creds, 'id_token') and creds.id_token:
            import jwt
            try:
                decoded = jwt.decode(creds.id_token, options={"verify_signature": False})
                if 'email' in decoded:
                    request.session["user_id"] = decoded['email']
                    logger.info(f"Updated user ID with email: {decoded['email']}")
            except Exception as e:
                logger.error(f"Error decoding id_token: {str(e)}")
        
        logger.info("Successfully obtained credentials")
        return RedirectResponse(url="/?status=authentication_successful")
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Authentication failed: {str(e)}" 