from flask import Flask, request, redirect, session, url_for
import os
import secrets
from libs.google_oauth import GoogleOAuthService
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a secure secret key

# Initialize the OAuth service
oauth_service = GoogleOAuthService(redirect_uri='http://localhost:5000/oauth2callback')

@app.route("/login")
def login():
    """Start the OAuth flow by redirecting to Google's auth page."""
    # Check if we already have valid credentials
    creds = oauth_service.get_credentials()
    if creds and creds.valid:
        return redirect(url_for('index', status='already_authenticated'))
    
    # Get authorization URL and state
    auth_url, state, flow = oauth_service.get_authorization_url()
    
    # Store the flow in the session for later use
    session['flow_state'] = state
    
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    """Handle the OAuth callback from Google."""
    try:
        logger.info("Received callback at /oauth2callback")
        logger.info(f"Request URL: {request.url}")
        logger.info(f"Request args: {request.args}")
        logger.info(f"Session data: {session}")
        
        # Check if there's an error in the callback
        if 'error' in request.args:
            error = request.args.get('error')
            logger.error(f"OAuth error: {error}")
            return f"Authentication failed: {error}"
        
        # Recreate the flow with the same redirect URI
        flow = oauth_service.create_authorization_flow()
        
        # Exchange the authorization code for credentials
        creds = oauth_service.fetch_token_from_response(flow, request.url)
        
        logger.info("Successfully obtained credentials")
        return redirect(url_for('index', status='authentication_successful'))
    except Exception as e:
        logger.error(f"Authentication failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return f"Authentication failed: {str(e)}"

@app.route('/')
def index():
    """Main page that shows authentication status."""
    status = request.args.get('status', '')
    
    creds = oauth_service.get_credentials()
    is_authenticated = creds and creds.valid
    
    if is_authenticated:
        return """
        <h1>OAuth Testing Server</h1>
        <p>Authentication status: <strong>Authenticated</strong></p>
        <p>You can now use the Gmail API.</p>
        """
    else:
        return """
        <h1>OAuth Testing Server</h1>
        <p>Authentication status: <strong>Not authenticated</strong></p>
        <p><a href="/login">Click here to authenticate with Google</a></p>
        """

if __name__ == "__main__":
    # Make sure the port matches your redirect URI
    app.run(debug=True, port=5000)