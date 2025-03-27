from flask import Flask, request, redirect
from google_auth_oauthlib.flow import Flow

app = Flask(__name__)

# Define the scopes you need
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

@app.route("/login")
def login():
    # Set up the OAuth flow with your client secrets and redirect URI
    flow = Flow.from_client_secrets_file(
        'config/client_secret.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:5000/oauth2callback'
    )
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true'
    )
    return redirect(auth_url)

@app.route("/oauth2callback")
def oauth2callback():
    # Recreate the flow to fetch the token using the current request URL
    flow = Flow.from_client_secrets_file(
        'config/client_secret.json',
        scopes=SCOPES,
        redirect_uri='http://localhost:5000/oauth2callback'
    )
    flow.fetch_token(authorization_response=request.url)
    credentials = flow.credentials
    # Now you can use the credentials to call the Gmail API
    return "Authentication successful! You can now use the Gmail API."

@app.route('/')
def index():
    return "Hello, welcome to the OAuth testing server."


if __name__ == "__main__":
    app.run(debug=True, port=5000)