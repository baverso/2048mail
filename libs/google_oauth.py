import os
import pickle
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.auth.exceptions import RefreshError
import logging
from libs.api_manager import get_google_api_config

logging.basicConfig(level=logging.INFO)

# Define the required OAuth scopes. For modifying Gmail (e.g., archiving), we need gmail.modify.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def get_gmail_credentials():
    """
    Authenticates with the Gmail API using OAuth and returns valid credentials.
    Uses a token.pickle file to store/reuse access tokens, and logs errors for troubleshooting.
    """
    creds = None
    # Store token.pickle in the config directory instead of root
    config_dir = os.path.join(os.path.dirname(__file__), '..', 'config')
    token_file = os.path.join(config_dir, 'token.pickle')
    
    # Ensure config directory exists
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        logging.info(f"Created config directory at {config_dir}")
    
    # Try to load the token file if it exists
    if os.path.exists(token_file):
        try:
            with open(token_file, 'rb') as token:
                creds = pickle.load(token)
            logging.info("Token file loaded successfully.")
        except Exception as e:
            logging.error(f"Error loading token file: {e}")
            creds = None
    else:
        logging.info("Token file not found; starting new authentication.")

    # If no valid credentials, initiate the OAuth flow
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                logging.info("Credentials refreshed successfully.")
            except RefreshError as re:
                logging.error(f"RefreshError: {re}. Token may have been revoked or expired.")
                creds = None  # Force reauthentication
            except Exception as e:
                logging.error(f"An error occurred during credentials refresh: {e}")
                creds = None
        
        if not creds:
            try:
                # Get Google API config from our centralized API manager
                google_config = get_google_api_config()
                
                # Create a temporary credentials.json file for the OAuth flow
                temp_credentials_file = os.path.join(config_dir, 'temp_credentials.json')
                with open(temp_credentials_file, 'w') as f:
                    json.dump(google_config, f)
                
                flow = InstalledAppFlow.from_client_secrets_file(temp_credentials_file, SCOPES)
                # Using a fixed port for consistency with your authorized redirect URI.
                creds = flow.run_local_server(port=8080)
                logging.info("New credentials obtained through OAuth flow.")
                
                # Clean up the temporary file
                os.remove(temp_credentials_file)
                
            except Exception as e:
                logging.error(f"OAuth flow failed: {e}")
                raise e  # Reraise after logging
        
        # Save the new credentials for future runs
        try:
            with open(token_file, 'wb') as token:
                pickle.dump(creds, token)
            logging.info("New token file saved successfully.")
        except Exception as e:
            logging.error(f"Failed to save token file: {e}")
    
    return creds