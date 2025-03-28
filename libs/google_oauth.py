import os
import pickle
import json
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import logging
from libs.api_manager import get_google_api_config

logging.basicConfig(level=logging.INFO)

# Define the required OAuth scopes. For modifying Gmail (e.g., archiving), we need gmail.modify.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

class GoogleOAuthService:
    def __init__(self, config_dir=None, redirect_uri=None):
        """Initialize the OAuth service with configuration directory and redirect URI."""
        if config_dir is None:
            self.config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
        else:
            self.config_dir = config_dir
            
        self.token_file = os.path.join(self.config_dir, 'token.pickle')
        self.redirect_uri = redirect_uri or 'http://localhost:5000/oauth2callback'
        
        # Ensure config directory exists
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)
            logging.info(f"Created config directory at {self.config_dir}")
    
    def get_credentials(self):
        """Get valid credentials, refreshing or loading from storage if possible."""
        creds = self._load_credentials()
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logging.info("Credentials refreshed successfully.")
                except (RefreshError, Exception) as e:
                    logging.error(f"Error refreshing credentials: {e}")
                    creds = None
            
            # If we still don't have valid credentials, we'll need to re-authenticate
            # But we don't start the flow here - that's handled by the web server
            if not creds:
                return None
                
            # Save refreshed credentials
            self._save_credentials(creds)
        
        return creds
    
    def create_authorization_flow(self):
        """Create and return an OAuth flow object."""
        google_config = get_google_api_config()
        
        # Create a temporary credentials file for the OAuth flow
        temp_credentials_file = os.path.join(self.config_dir, 'temp_credentials.json')
        with open(temp_credentials_file, 'w') as f:
            json.dump(google_config, f)
        
        try:
            flow = Flow.from_client_secrets_file(
                temp_credentials_file,
                scopes=SCOPES,
                redirect_uri=self.redirect_uri
            )
            # Clean up the temporary file
            os.remove(temp_credentials_file)
            return flow
        except Exception as e:
            logging.error(f"Failed to create authorization flow: {e}")
            if os.path.exists(temp_credentials_file):
                os.remove(temp_credentials_file)
            raise
    
    def get_authorization_url(self):
        """Get the authorization URL for the OAuth flow."""
        flow = self.create_authorization_flow()
        
        # Log the client ID being used
        logging.info(f"Using client ID: {flow._client_config['client_id']}")
        logging.info(f"Redirect URI: {flow.redirect_uri}")
        
        auth_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent'  # Force the consent screen to appear
        )
        
        logging.info(f"Generated authorization URL: {auth_url}")
        return auth_url, state, flow
    
    def fetch_token_from_response(self, flow, authorization_response):
        """Exchange authorization response for tokens."""
        try:
            logging.info(f"Fetching token from response: {authorization_response}")
            flow.fetch_token(authorization_response=authorization_response)
            creds = flow.credentials
            logging.info("Token fetched successfully")
            self._save_credentials(creds)
            return creds
        except Exception as e:
            logging.error(f"Error fetching token: {e}")
            import traceback
            logging.error(traceback.format_exc())
            raise
    
    def _load_credentials(self):
        """Load credentials from the token file."""
        if os.path.exists(self.token_file):
            try:
                with open(self.token_file, 'rb') as token:
                    return pickle.load(token)
            except Exception as e:
                logging.error(f"Error loading token file: {e}")
        return None
    
    def _save_credentials(self, creds):
        """Save credentials to the token file."""
        try:
            with open(self.token_file, 'wb') as token:
                pickle.dump(creds, token)
            logging.info("Token file saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save token file: {e}")