import os
import secrets
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# Adding a custom filter to suppress repetitive server status logs
class StatusLogFilter(logging.Filter):
    def filter(self, record):
        if "User background_task" in record.getMessage():
            return False
        return True

logger.addFilter(StatusLogFilter())


class Settings:
    """Application settings."""
    # Server configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = True
    LOG_LEVEL: str = "warning"
    ACCESS_LOG: bool = False
    
    # Session configuration
    SESSION_SECRET_KEY: str = secrets.token_hex(32)  # Generate a new secure random key
    
    # OAuth configuration
    OAUTH_REDIRECT_URI: str = "http://localhost:8000/oauth2callback"
    
    # Templates configuration
    TEMPLATES_DIR: str = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates')
    
    @classmethod
    def initialize(cls):
        """Initialize settings, ensuring directories exist."""
        # Create templates directory if it doesn't exist
        os.makedirs(cls.TEMPLATES_DIR, exist_ok=True)
        logger.info(f"Using secret key: {cls.SESSION_SECRET_KEY[:8]}...{cls.SESSION_SECRET_KEY[-8:]}")


# Create a settings instance
settings = Settings()
settings.initialize() 