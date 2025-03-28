import os
import json
import logging
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_api_keys():
    """
    Load API keys from the config/api_keys.json file or environment variables.
    
    Returns:
        dict: A dictionary containing API keys.
    """
    # Define the path to the API keys file
    api_keys_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'api_keys.json')
    
    # Check if the file exists
    if os.path.exists(api_keys_path):
        try:
            with open(api_keys_path, 'r') as f:
                keys = json.load(f)
            logger.info("API keys loaded from file.")
            return keys
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing API keys file: {e}")
            # Fall back to environment variables
    
    # If file doesn't exist or couldn't be parsed, use environment variables
    logger.info("Using API keys from environment variables.")
    return {
        "openai": {
            "api_key": os.environ.get("OPENAI_API_KEY")
        }
    }

def get_google_api_config():
    """
    Load Google API configuration from credentials file.
    
    Returns:
        dict: A dictionary containing Google API configuration.
    """
    # Define the path to the Google credentials file
    google_credentials_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'google_credentials.json')
    
    # Check if the file exists
    if os.path.exists(google_credentials_path):
        try:
            with open(google_credentials_path, 'r') as f:
                config = json.load(f)
            logger.info("Google API credentials loaded from file.")
            return config
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing Google credentials file: {e}")
            raise
    else:
        logger.error("Google credentials file not found at: %s", google_credentials_path)
        raise FileNotFoundError(f"Google credentials file not found at: {google_credentials_path}")

def setup_openai_api():
    """
    Set up the OpenAI API by setting the API key in the environment.
    """
    keys = load_api_keys()
    
    # Set the OpenAI API key in the environment
    if "openai" in keys and "api_key" in keys["openai"]:
        os.environ["OPENAI_API_KEY"] = keys["openai"]["api_key"]
        logger.info("OpenAI API key set in environment.")
    else:
        # Check if it's already in the environment
        if not os.environ.get("OPENAI_API_KEY"):
            logger.warning("OpenAI API key not found in config or environment.")

def setup_all_apis():
    """
    Set up all API keys at once.
    """
    keys = load_api_keys()
    
    # Set up OpenAI API
    if "openai" in keys and "api_key" in keys["openai"]:
        os.environ["OPENAI_API_KEY"] = keys["openai"]["api_key"]
        logger.info("OpenAI API key loaded successfully")
    else:
        logger.warning("OpenAI API key not found in config")
    
    # Add other API setups here as needed
    
    return keys 