import os
import json
import logging
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

def load_api_keys():
    """
    Load API keys from configuration file.
    Looks for config/api_keys.json in the project root directory.
    
    Returns:
        dict: Dictionary containing all API keys
    """
    try:
        # Use Path for cross-platform compatibility
        config_path = Path(__file__).parent.parent / "config" / "api_keys.json"
        with open(config_path) as f:
            keys = json.load(f)
        return keys
    except FileNotFoundError:
        logger.error(
            "API keys file not found. Please create config/api_keys.json "
            "using config/api_keys.template.json as a template."
        )
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON in api_keys.json")
        raise

def setup_openai_api():
    """
    Load OpenAI API key and set it as an environment variable.
    """
    keys = load_api_keys()
    if "openai_api_key" in keys:
        os.environ["OPENAI_API_KEY"] = keys["openai_api_key"]
        logger.info("OpenAI API key loaded successfully")
    else:
        logger.error("OpenAI API key not found in config/api_keys.json")
        raise KeyError("OpenAI API key not found in config")

def get_google_api_config():
    """
    Get Google API configuration from the API keys file.
    
    Returns:
        dict: Google API configuration
    """
    keys = load_api_keys()
    if "google" in keys:
        return keys["google"]
    else:
        logger.error("Google API configuration not found in config/api_keys.json")
        raise KeyError("Google API configuration not found in config")

def setup_all_apis():
    """
    Set up all API keys at once.
    """
    keys = load_api_keys()
    
    # Set up OpenAI API
    if "openai_api_key" in keys:
        os.environ["OPENAI_API_KEY"] = keys["openai_api_key"]
        logger.info("OpenAI API key loaded successfully")
    else:
        logger.warning("OpenAI API key not found in config")
    
    # Add other API setups here as needed
    
    return keys 