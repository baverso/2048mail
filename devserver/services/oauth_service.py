from typing import Optional, Tuple, Any
import logging
from abc import ABC, abstractmethod
from fastapi import Request, Depends

from libs.google_oauth import GoogleOAuthService

logger = logging.getLogger(__name__)

class OAuthServiceInterface(ABC):
    """Interface for OAuth services to allow for dependency injection."""
    
    @abstractmethod
    def get_credentials(self) -> Any:
        """Get the current OAuth credentials."""
        pass
    
    @abstractmethod
    def get_authorization_url(self) -> Tuple[str, str, Any]:
        """Get the authorization URL for the OAuth flow."""
        pass
    
    @abstractmethod
    def create_authorization_flow(self) -> Any:
        """Create a new authorization flow."""
        pass
    
    @abstractmethod
    def fetch_token_from_response(self, flow: Any, callback_url: str) -> Any:
        """Fetch OAuth token from the callback response."""
        pass


class GoogleOAuthServiceAdapter(OAuthServiceInterface):
    """Adapter for the GoogleOAuthService to implement the OAuthServiceInterface."""
    
    def __init__(self, redirect_uri: str = 'http://localhost:8000/oauth2callback'):
        self.service = GoogleOAuthService(redirect_uri=redirect_uri)
    
    def get_credentials(self) -> Any:
        """Get the current OAuth credentials."""
        return self.service.get_credentials()
    
    def get_authorization_url(self) -> Tuple[str, str, Any]:
        """Get the authorization URL for the OAuth flow."""
        return self.service.get_authorization_url()
    
    def create_authorization_flow(self) -> Any:
        """Create a new authorization flow."""
        return self.service.create_authorization_flow()
    
    def fetch_token_from_response(self, flow: Any, callback_url: str) -> Any:
        """Fetch OAuth token from the callback response."""
        return self.service.fetch_token_from_response(flow, callback_url)


# Factory function for dependency injection
def get_oauth_service() -> OAuthServiceInterface:
    """Get the OAuth service implementation."""
    return GoogleOAuthServiceAdapter()


# Convenience function to check if a user is authenticated
async def is_authenticated(
    oauth_service: OAuthServiceInterface = Depends(get_oauth_service)
) -> bool:
    """Check if the current user is authenticated."""
    creds = oauth_service.get_credentials()
    return creds is not None and creds.valid


# Function to get user email from credentials
async def get_user_email(
    oauth_service: OAuthServiceInterface = Depends(get_oauth_service)
) -> Optional[str]:
    """Get the email of the authenticated user."""
    creds = oauth_service.get_credentials()
    if creds and creds.valid and hasattr(creds, 'id_token') and creds.id_token:
        # Try to extract email from id_token if available
        import jwt
        try:
            decoded = jwt.decode(creds.id_token, options={"verify_signature": False})
            if 'email' in decoded:
                return decoded['email']
        except Exception as e:
            logger.error(f"Error decoding id_token: {str(e)}")
    
    return None