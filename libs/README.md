# Libs Directory

This directory contains utility libraries and modules used throughout the application.

## API Manager

The `api_manager.py` module provides centralized API key management for the application. It handles:

- Loading API keys from the configuration file
- Setting up environment variables for various APIs
- Providing access to API configurations for other modules

### Usage

```python
# To set up the OpenAI API (sets the OPENAI_API_KEY environment variable)
from libs.api_manager import setup_openai_api
setup_openai_api()

# To get Google API configuration
from libs.api_manager import get_google_api_config
google_config = get_google_api_config()

# To set up all APIs at once
from libs.api_manager import setup_all_apis
api_keys = setup_all_apis()
```

## Google OAuth

The `google_oauth.py` module handles authentication with Google APIs using OAuth. It uses the API manager to retrieve Google API credentials.

### Usage

```python
from libs.google_oauth import get_gmail_credentials
credentials = get_gmail_credentials()
```

## Configuration

All API keys and credentials should be stored in the `config/api_keys.json` file. See the template in `config/api_keys.template.json` for the expected format. 