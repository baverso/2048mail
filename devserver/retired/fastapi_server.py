import os
import secrets
import logging
import threading
import queue
import uvicorn
from typing import Optional, Dict, Any, List, DefaultDict
from collections import defaultdict
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

# Import the OAuth service
from libs.google_oauth import GoogleOAuthService

# Import the web feedback module instead of human_feedback
from tools.web_feedback import register_connection_manager, provide_feedback, get_user_state as get_web_feedback_user_state, set_current_user_id
from agents.orchestrator_text_completions import orchestrate_email_response

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

# Initialize FastAPI app
app = FastAPI(title="Quillo Email Management System")
# Use a fixed secret key for easier debugging
SESSION_SECRET_KEY = "secret_cookie_key"  # Using a fixed key for debugging
app.add_middleware(SessionMiddleware, secret_key=SESSION_SECRET_KEY)

# For handling process feedback globally
LAST_CONNECTED_USER_ID = None

# Initialize the OAuth service
oauth_service = GoogleOAuthService(redirect_uri='http://localhost:8000/oauth2callback')

# Create templates directory
templates_dir = os.path.join(os.path.dirname(__file__), 'templates')
os.makedirs(templates_dir, exist_ok=True)
templates = Jinja2Templates(directory=templates_dir)

# User-specific task trackers
class UserTaskState:
    def __init__(self):
        self.background_task = {
            "running": False,
            "status": "idle",
            "results": None,
            "current_email": None,
            "feedback_required": False,
            "user_id": None
        }

# Dictionary to store user-specific task states
user_states = {}

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        # Dictionary mapping user IDs to their active WebSocket connections
        self.user_connections: DefaultDict[str, List[WebSocket]] = defaultdict(list)
        # Dictionary mapping WebSocket objects to user IDs for quick lookup
        self.connection_to_user: Dict[WebSocket, str] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        # Accept the incoming WebSocket connection
        await websocket.accept()
        # Add the new connection to our dictionary under the user's ID
        self.user_connections[user_id].append(websocket)
        # Store the reverse mapping
        self.connection_to_user[websocket] = user_id
        logger.info(f"WebSocket connected for user {user_id}")

    def disconnect(self, websocket: WebSocket):
        # Get the user ID associated with this WebSocket
        user_id = self.connection_to_user.get(websocket)
        if user_id:
            # Remove the WebSocket from the user's connections
            if websocket in self.user_connections[user_id]:
                self.user_connections[user_id].remove(websocket)
            # Clean up empty user entries
            if not self.user_connections[user_id]:
                del self.user_connections[user_id]
            # Remove the reverse mapping
            del self.connection_to_user[websocket]
            logger.info(f"WebSocket disconnected for user {user_id}")

    async def send_to_user(self, user_id: str, message: Dict[str, Any]):
        """Send a message to all connections belonging to a specific user."""
        if user_id in self.user_connections:
            for connection in self.user_connections[user_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message to user {user_id}: {str(e)}")
        else:
            logger.warning(f"No active connections for user {user_id}")

    async def broadcast(self, message: Dict[str, Any]):
        """Send a message to all connected clients (for backward compatibility)."""
        logger.warning("SECURITY RISK: Using broadcast which sends to all users - this should NEVER be used with sensitive data")
        logger.warning("This method should be removed or restricted in production environments")
        for user_id in self.user_connections:
            await self.send_to_user(user_id, message)

    def get_user_id(self, websocket: WebSocket) -> Optional[str]:
        """Get the user ID associated with a WebSocket connection."""
        return self.connection_to_user.get(websocket)

manager = ConnectionManager()

# Register the connection manager with the web_feedback module
register_connection_manager(manager)

# Helper function to extract draft email data from various possible structures
def extract_draft_email_data(results):
    """
    Extract draft email data from results returned by the orchestrator.
    This handles multiple possible structures to ensure we can always find the draft email.
    """
    draft_email = None
    draft_subject = None
    draft_recipient = None
    
    # Case 1: Direct top-level fields
    if isinstance(results, dict):
        if "draft_email" in results:
            draft_email = results["draft_email"]
            draft_subject = results.get("draft_subject", "")
            draft_recipient = results.get("draft_recipient", "")
            logger.info("Found draft email at top level of results.")
            
        # Case 2: Nested in latest_draft
        elif "latest_draft" in results:
            latest_draft = results["latest_draft"]
            if isinstance(latest_draft, dict) and "draft_email" in latest_draft:
                draft_email = latest_draft["draft_email"]
                draft_subject = latest_draft.get("draft_subject", "")
                draft_recipient = latest_draft.get("draft_recipient", "")
                logger.info("Found draft email in latest_draft field.")
                
        # Case 3: Nested in details.latest_draft
        elif "details" in results and isinstance(results["details"], dict):
            details = results["details"]
            if "latest_draft" in details:
                latest_draft = details["latest_draft"]
                if isinstance(latest_draft, dict) and "draft_email" in latest_draft:
                    draft_email = latest_draft["draft_email"]
                    draft_subject = latest_draft.get("draft_subject", "")
                    draft_recipient = latest_draft.get("draft_recipient", "")
                    logger.info("Found draft email in details.latest_draft.")
                    
    if draft_email:
        logger.info(f"Successfully extracted draft email (length: {len(draft_email)})")
    else:
        logger.info("No draft email found in any expected location in results")
        
    return draft_email, draft_subject, draft_recipient

# Helper function to get or create a user state
def get_user_state(user_id: str) -> UserTaskState:
    """Get or create a user state based on user ID."""
    if user_id not in user_states:
        user_states[user_id] = UserTaskState()
    return user_states[user_id]

# Function to get the current user ID from the request
async def get_current_user_id(request: Request) -> str:
    """
    Get the current user ID from the session or create a new one.
    Returns a unique user ID for the session.
    """
    if "user_id" not in request.session or request.session["user_id"] == "none":
        # Get user information from OAuth if available
        creds = oauth_service.get_credentials()
        if creds and creds.valid and hasattr(creds, 'id_token') and creds.id_token:
            # Try to extract email from id_token if available
            import jwt
            try:
                decoded = jwt.decode(creds.id_token, options={"verify_signature": False})
                if 'email' in decoded:
                    request.session["user_id"] = decoded['email']
                    logger.info(f"Using email as user ID: {decoded['email']}")
                else:
                    request.session["user_id"] = str(uuid.uuid4())
            except Exception as e:
                logger.error(f"Error decoding id_token: {str(e)}")
                request.session["user_id"] = str(uuid.uuid4())
        else:
            # Generate a new random user ID if not authenticated
            request.session["user_id"] = str(uuid.uuid4())
        
        logger.info(f"Created new user ID: {request.session['user_id']}")
    
    # Always prefer the last connected user ID if available, for consistency
    global LAST_CONNECTED_USER_ID
    if LAST_CONNECTED_USER_ID:
        logger.info(f"Using last connected user ID instead of session: {LAST_CONNECTED_USER_ID}")
        return LAST_CONNECTED_USER_ID
    
    return request.session["user_id"]

# Pydantic models for API requests/responses
class FeedbackRequest(BaseModel):
    feedback: bool = True

class StatusResponse(BaseModel):
    running: bool
    status: str
    results: Optional[Any] = None
    feedback_required: bool
    current_prompt: Optional[str] = None
    current_decision: Optional[str] = None
    current_context: Optional[str] = None
    draft_email: Optional[str] = None
    draft_subject: Optional[str] = None
    draft_recipient: Optional[str] = None

# Routes
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Main page that shows authentication status and email processing options."""
    # Check if authenticated
    creds = oauth_service.get_credentials()
    is_authenticated = creds and creds.valid
    
    # Get or create user ID
    user_id = await get_current_user_id(request)
    user_state = get_user_state(user_id)
    
    # Create index.html if it doesn't exist
    index_html_path = os.path.join(templates_dir, 'index.html')
    if not os.path.exists(index_html_path):
        with open(index_html_path, 'w') as f:
            f.write("""
<!DOCTYPE html>
<html>
<head>
    <title>Quillo Email Management System</title>
    <script>
        let socket;
        let reconnectInterval;
        let lastFeedbackState = false;
        
        function connectWebSocket() {
            if (socket && socket.readyState !== WebSocket.CLOSED) {
                console.log("WebSocket already connected or connecting");
                return;
            }
            
            clearInterval(reconnectInterval);
            
            socket = new WebSocket(`ws://${window.location.host}/ws`);
            
            socket.onopen = function(e) {
                console.log("WebSocket connection established");
                document.getElementById('connection-status').textContent = 'Connected';
                document.getElementById('connection-status').style.color = 'green';
                
                // Clear any reconnect timer
                clearInterval(reconnectInterval);
            };
            
            socket.onmessage = function(event) {
                const data = JSON.parse(event.data);
                console.log("Message received:", data);
                
                if (data.type === 'feedback_required') {
                    document.getElementById('feedback-container').style.display = 'block';
                    document.getElementById('feedback-prompt').textContent = data.prompt || 'Provide feedback:';
                    document.getElementById('feedback-decision').textContent = data.decision || '';
                    document.getElementById('feedback-context').textContent = data.context || '';
                    
                    // Flash the feedback container to get attention
                    flashElement('feedback-container');
                    
                    // Also show a notification if browser supports it
                    showNotification('Feedback Required', data.prompt || 'Please provide feedback');
                    
                    lastFeedbackState = true;
                } else if (data.type === 'status_update') {
                    updateStatus(data);
                } else if (data.type === 'feedback_timeout') {
                    alert(data.message);
                    document.getElementById('feedback-container').style.display = 'none';
                    lastFeedbackState = false;
                } else if (data.type === 'feedback_received') {
                    console.log("Feedback received by server.");
                    lastFeedbackState = false;
                }
            };
            
            socket.onclose = function(event) {
                document.getElementById('connection-status').textContent = 'Disconnected';
                document.getElementById('connection-status').style.color = 'red';
                
                if (event.wasClean) {
                    console.log(`Connection closed cleanly, code=${event.code} reason=${event.reason}`);
                } else {
                    console.log('Connection died');
                }
                
                // Retry connection after 3 seconds
                if (!reconnectInterval) {
                    reconnectInterval = setTimeout(connectWebSocket, 3000);
                }
            };
            
            socket.onerror = function(error) {
                console.log(`WebSocket error: ${error.message}`);
                document.getElementById('connection-status').textContent = 'Error';
                document.getElementById('connection-status').style.color = 'red';
            };
        }
        
        function showNotification(title, body) {
            if (!("Notification" in window)) {
                console.log("This browser does not support desktop notification");
                return;
            }
            
            if (Notification.permission === "granted") {
                const notification = new Notification(title, { body });
                notification.onclick = function() {
                    window.focus();
                    this.close();
                };
            } else if (Notification.permission !== "denied") {
                Notification.requestPermission().then(function (permission) {
                    if (permission === "granted") {
                        const notification = new Notification(title, { body });
                        notification.onclick = function() {
                            window.focus();
                            this.close();
                        };
                    }
                });
            }
        }
        
        function flashElement(elementId) {
            const element = document.getElementById(elementId);
            if (!element) return;
            
            let count = 6;
            const interval = setInterval(() => {
                element.style.backgroundColor = count % 2 === 0 ? '#ffe0e0' : '#f0f0f0';
                count--;
                if (count <= 0) {
                    clearInterval(interval);
                    element.style.backgroundColor = '#f0f0f0';
                }
            }, 500);
        }
        
        function provideFeedback(value) {
            if (socket && socket.readyState === WebSocket.OPEN) {
                socket.send(JSON.stringify({
                    type: 'provide_feedback',
                    feedback: value
                }));
                document.getElementById('feedback-container').style.display = 'none';
                lastFeedbackState = false;
            } else {
                alert('WebSocket connection is not open. Trying to reconnect...');
                connectWebSocket();
                
                // Also send feedback via HTTP as fallback
                fetch('/provide-feedback', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({ feedback: value }),
                })
                .then(response => response.json())
                .then(data => {
                    console.log('Feedback provided via HTTP:', data);
                    document.getElementById('feedback-container').style.display = 'none';
                })
                .catch(error => {
                    console.error('Error providing feedback via HTTP:', error);
                    alert('Failed to send feedback. Please try again.');
                });
            }
        }
        
        function processEmails() {
            fetch('/process-emails')
                .then(response => response.json())
                .then(data => {
                    console.log('Process emails response:', data);
                    document.getElementById('status').textContent = data.status;
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        }
        
        function updateStatus(data) {
            document.getElementById('status').textContent = data.status;
            if (data.results) {
                document.getElementById('results').textContent = JSON.stringify(data.results, null, 2);
            }
            
            // Check if there's a draft email to display
            const draftContainer = document.getElementById('draft-container');
            console.log("updateStatus called with data:", data);
            console.log("Data keys:", Object.keys(data));
            console.log("Draft email present:", !!data.draft_email);
            console.log("Draft email type:", typeof data.draft_email);
            
            if (data.draft_email) {
                console.log("Showing draft container with subject:", data.draft_subject);
                console.log("Draft recipient:", data.draft_recipient);
                console.log("Draft email length:", data.draft_email.length);
                console.log("Draft email preview:", data.draft_email.substring(0, 100));
                
                draftContainer.style.display = 'block';
                document.getElementById('draft-subject').textContent = data.draft_subject || 'No subject';
                document.getElementById('draft-recipient').textContent = data.draft_recipient || 'No recipient';
                document.getElementById('draft-content').textContent = data.draft_email;
                
                console.log("Draft container display style:", draftContainer.style.display);
                console.log("Draft content element:", document.getElementById('draft-content'));
                console.log("Draft container visible:", draftContainer.offsetParent !== null);
                
                // Scroll to the draft container
                draftContainer.scrollIntoView({ behavior: 'smooth', block: 'start' });
                console.log("Scrolled to draft container");
            } else {
                console.log("Hiding draft container");
                draftContainer.style.display = 'none';
            }
            
            // If feedback is required, show the feedback container
            if (data.feedback_required && !lastFeedbackState) {
                document.getElementById('feedback-container').style.display = 'block';
                document.getElementById('feedback-prompt').textContent = data.current_prompt || 'Provide feedback:';
                document.getElementById('feedback-decision').textContent = data.current_decision || '';
                document.getElementById('feedback-context').textContent = data.current_context || '';
                
                // Flash the feedback container to get attention
                flashElement('feedback-container');
                
                // Also show a notification if browser supports it
                showNotification('Feedback Required', data.current_prompt || 'Please provide feedback');
                
                lastFeedbackState = true;
            } else if (!data.feedback_required && lastFeedbackState) {
                document.getElementById('feedback-container').style.display = 'none';
                lastFeedbackState = false;
            }
        }
        
        function checkStatus() {
            fetch('/status')
                .then(response => response.json())
                .then(data => {
                    updateStatus(data);
                })
                .catch(error => {
                    console.error('Error:', error);
                });
        }
        
        document.addEventListener('DOMContentLoaded', function() {
            // Request notification permission
            if ("Notification" in window && Notification.permission !== "granted") {
                Notification.requestPermission();
            }
            
            // Check if draft container exists
            const draftContainer = document.getElementById('draft-container');
            console.log("Draft container exists:", !!draftContainer);
            if (draftContainer) {
                console.log("Draft container initial display:", draftContainer.style.display);
            }
            
            connectWebSocket();
            // Poll status every 5 seconds as a fallback
            setInterval(checkStatus, 5000);
        });
    </script>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .container { max-width: 800px; margin: 0 auto; }
        .feedback-container { 
            display: none; 
            background-color: #f0f0f0; 
            padding: 20px; 
            margin-top: 20px;
            border-radius: 5px;
            border: 2px solid #ddd;
            transition: background-color 0.5s ease;
        }
        .draft-container {
            display: none;
            background-color: #f0fff0;
            padding: 20px;
            margin-top: 20px;
            border-radius: 5px;
            border: 2px solid #cce6cc;
        }
        .draft-email {
            white-space: pre-wrap;
            background: #ffffff;
            padding: 15px;
            border-radius: 5px;
            border: 1px solid #ddd;
            margin-top: 10px;
        }
        .notice {
            background-color: #fffde7;
            padding: 10px;
            border-left: 4px solid #ffd600;
            margin: 10px 0;
        }
        button { padding: 10px 20px; margin-right: 10px; cursor: pointer; }
        .status-container { margin-top: 20px; }
        pre { white-space: pre-wrap; background: #f5f5f5; padding: 10px; border-radius: 5px; max-height: 300px; overflow-y: auto; }
        .status-badge {
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Email Management System</h1>
        <p>WebSocket status: <span id="connection-status" style="font-weight: bold;">Connecting...</span></p>
        
        {% if is_authenticated %}
            <p>Authentication status: <strong class="status-badge" style="background-color: #c8f7c5;">Authenticated</strong></p>
            <p>User ID: <strong>{{ user_id }}</strong></p>
            <p>You can now use the Gmail API.</p>
            <button onclick="processEmails()">Process Emails</button>
            
            <div class="status-container">
                <h2>Status</h2>
                <p>Current status: <span id="status" class="status-badge" style="background-color: #f1f1f1;">{{ status }}</span></p>
                <pre id="results"></pre>
            </div>
            
            <div id="draft-container" class="draft-container">
                <h2>Email Draft Created</h2>
                <div class="notice">
                    <p><strong>Note:</strong> This email has been saved to your Gmail drafts folder. You can review and send it at your convenience.</p>
                </div>
                <p><strong>To:</strong> <span id="draft-recipient"></span></p>
                <p><strong>Subject:</strong> <span id="draft-subject"></span></p>
                <h3>Email Content:</h3>
                <div id="draft-content" class="draft-email"></div>
            </div>
            
            <div id="feedback-container" class="feedback-container">
                <h2>Feedback Required</h2>
                <p id="feedback-prompt">Provide feedback:</p>
                <p>Decision: <strong id="feedback-decision"></strong></p>
                <p>Context: <pre id="feedback-context"></pre></p>
                <button onclick="provideFeedback(true)" style="background-color: #4CAF50; color: white;">Correct ✓</button>
                <button onclick="provideFeedback(false)" style="background-color: #f44336; color: white;">Wrong ✗</button>
            </div>
        {% else %}
            <p>Authentication status: <strong class="status-badge" style="background-color: #ffcccc;">Not authenticated</strong></p>
            <p><a href="/login">Click here to authenticate with Google</a></p>
        {% endif %}
    </div>
</body>
</html>
            """)
    
    return templates.TemplateResponse("index.html", {
        "request": request, 
        "is_authenticated": is_authenticated,
        "status": user_state.background_task["status"],
        "user_id": user_id
    })

@app.get("/login")
async def login():
    """Start the OAuth flow by redirecting to Google's auth page."""
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

@app.get("/oauth2callback")
async def oauth2callback(request: Request):
    """Handle the OAuth callback from Google."""
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

@app.get("/process-emails")
async def process_emails(request: Request):
    """Start processing emails in the background."""
    # Get current user ID
    user_id = await get_current_user_id(request)
    logger.info(f"Process-emails endpoint called by user {user_id}")
    
    user_state = get_user_state(user_id)
    
    # Check if already running
    if user_state.background_task["running"]:
        logger.info(f"Email processing is already running for user {user_id}")
        return JSONResponse({
            "status": "already_running",
            "message": "Email processing is already running."
        })
    
    # Check authentication
    creds = oauth_service.get_credentials()
    if not creds or not creds.valid:
        logger.info(f"User {user_id} is not authenticated, cannot process emails")
        return JSONResponse({
            "status": "not_authenticated",
            "message": "You need to authenticate first."
        })
    
    # Use the last connected WebSocket user ID if available
    global LAST_CONNECTED_USER_ID
    if LAST_CONNECTED_USER_ID:
        logger.info(f"Using last connected WebSocket user ID: {LAST_CONNECTED_USER_ID} instead of session user ID: {user_id}")
        user_id = LAST_CONNECTED_USER_ID
    
    # Set the current user ID in the web_feedback module
    set_current_user_id(user_id)
    logger.info(f"Starting email processing for user: {user_id}")
    
    # Start background thread
    user_state.background_task["running"] = True
    user_state.background_task["status"] = "starting"
    user_state.background_task["results"] = None
    user_state.background_task["user_id"] = user_id
    
    def process_emails_task():
        # Store thread name for later identification
        thread_name = threading.current_thread().name
        user_state.background_task["thread_name"] = thread_name
        
        user_state.background_task["status"] = "running"
        try:
            # Define the draft callback function
            def draft_callback(draft_data):
                logger.info(f"Draft callback received data with keys: {list(draft_data.keys())}")
                
                # Store the draft data in the user's state
                user_state.background_task["draft_email"] = draft_data.get("draft_email")
                user_state.background_task["draft_subject"] = draft_data.get("draft_subject")
                user_state.background_task["draft_recipient"] = draft_data.get("draft_recipient")
                user_state.background_task["results"] = draft_data
                
                logger.info(f"Stored draft in user state. Email length: {len(user_state.background_task['draft_email'])}")
                
                # Send notification via WebSocket
                def send_draft_update():
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    
                    status_data = {
                        'type': 'status_update',
                        'status': "draft_created",
                        'results': draft_data,
                        'draft_email': draft_data.get("draft_email"),
                        'draft_subject': draft_data.get("draft_subject"),
                        'draft_recipient': draft_data.get("draft_recipient")
                    }
                    
                    logger.info(f"Sending draft notification to user {user_id}")
                    if hasattr(manager, 'user_connections') and user_id in manager.user_connections:
                        loop.run_until_complete(
                            manager.send_to_user(user_id, status_data)
                        )
                        logger.info(f"Draft notification sent to user {user_id}")
                    else:
                        logger.warning(f"No WebSocket connection for user {user_id}, draft notification not sent")
                    
                    loop.close()
                
                # Send the notification in a separate thread to avoid blocking
                notification_thread = threading.Thread(target=send_draft_update)
                notification_thread.daemon = True
                notification_thread.start()
            
            # Pass the user_id and draft_callback to the orchestrator
            logger.info(f"Calling orchestrator for user_id: {user_id} with draft callback")
            results = orchestrate_email_response(user_id=user_id, draft_callback=draft_callback)
            logger.info(f"Orchestrator returned results type: {type(results)}")
            
            # Check if results is a string (old behavior) or a dict with more details
            if isinstance(results, dict):
                logger.info(f"Results is a dictionary with keys: {list(results.keys())}")
                # Log all keys and their types
                for key, value in results.items():
                    if isinstance(value, str) and len(value) > 100:
                        logger.info(f"Results[{key}] = {type(value)} with length {len(value)}")
                    else:
                        logger.info(f"Results[{key}] = {type(value)}")
                
                user_state.background_task["results"] = results
                
                # Use the extract_draft_email_data function to robustly get draft email data
                draft_email, draft_subject, draft_recipient = extract_draft_email_data(results)
                
                if draft_email:
                    logger.info(f"Successfully extracted draft email data, storing in user state")
                    user_state.background_task["draft_email"] = draft_email
                    user_state.background_task["draft_subject"] = draft_subject
                    user_state.background_task["draft_recipient"] = draft_recipient
                    logger.info(f"Draft email length: {len(draft_email)} chars")
                    logger.info(f"Draft subject: {draft_subject}")
                    logger.info(f"Draft recipient: {draft_recipient}")
                    
                    # Verify the email was stored correctly
                    logger.info(f"Verifying draft email storage: {user_state.background_task['draft_email'] is not None}")
                    logger.info(f"Stored draft email length: {len(user_state.background_task['draft_email'])}")
                else:
                    logger.info("No draft email found in results dictionary")
            else:
                logger.info(f"Results is a string: {results[:100]}...")
                user_state.background_task["results"] = results
                
            user_state.background_task["status"] = "completed"
            
            # Add a verification log
            logger.info(f"Processing completed. Task status set to 'completed'. Draft email present: {'draft_email' in user_state.background_task}")
            
            # Send status update only to the user who started the task
            def send_status_update():
                import asyncio
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                # Log what we're sending to the user
                status_data = {
                    'type': 'status_update',
                    'status': user_state.background_task["status"],
                    'results': user_state.background_task["results"],
                    'draft_email': user_state.background_task.get("draft_email"),
                    'draft_subject': user_state.background_task.get("draft_subject"),
                    'draft_recipient': user_state.background_task.get("draft_recipient")
                }
                
                # Double check draft_email is included
                if not status_data.get('draft_email') and user_state.background_task.get("results"):
                    # Try to extract draft email using our robust function
                    draft_email, draft_subject, draft_recipient = extract_draft_email_data(user_state.background_task["results"])
                    if draft_email:
                        logger.info("Found draft email using extraction function, adding to status update")
                        status_data['draft_email'] = draft_email
                        status_data['draft_subject'] = draft_subject
                        status_data['draft_recipient'] = draft_recipient
                
                # Log all keys in the status_data message
                logger.info(f"Status update data keys: {list(status_data.keys())}")
                
                has_draft = status_data.get('draft_email') is not None
                logger.info(f"Sending status update to user {user_id} with draft email: {'Yes' if has_draft else 'No'}")
                if has_draft:
                    logger.info(f"Draft data being sent via WebSocket - length: {len(status_data['draft_email'])}")
                    logger.info(f"Draft data first 100 chars: {status_data['draft_email'][:100]}")
                else:
                    # Log the entire user_state to see if draft_email exists elsewhere
                    logger.info(f"No draft email in status_data, checking user_state")
                    for key, value in user_state.background_task.items():
                        if isinstance(value, str) and len(value) > 100:
                            logger.info(f"user_state.background_task[{key}] = {type(value)} with length {len(value)}")
                        else:
                            logger.info(f"user_state.background_task[{key}] = {type(value)}")
                
                # Check if user has an active WebSocket connection
                has_connection = False
                if hasattr(manager, 'user_connections') and user_id in manager.user_connections:
                    has_connection = True
                    logger.info(f"User {user_id} has active WebSocket connection: {len(manager.user_connections[user_id])} connection(s)")
                else:
                    logger.warning(f"User {user_id} has NO active WebSocket connections")
                
                if has_connection:
                    loop.run_until_complete(
                        manager.send_to_user(user_id, status_data)
                    )
                    logger.info(f"Status update sent to user {user_id}")
                else:
                    logger.error(f"Could not send status update - no active connection")
                
                loop.close()
            
            threading.Thread(target=send_status_update).start()
            
        except Exception as e:
            user_state.background_task["status"] = "failed"
            user_state.background_task["results"] = str(e)
            logger.error(f"Email processing failed for user {user_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
        finally:
            user_state.background_task["running"] = False
    
    thread = threading.Thread(target=process_emails_task)
    thread.daemon = True
    thread.start()
    
    return JSONResponse({
        "status": "started",
        "message": "Email processing started in the background."
    })

@app.get("/status", response_model=StatusResponse)
async def status(request: Request):
    """Check the status of the email processing task."""
    # Get current user ID
    user_id = await get_current_user_id(request)
    logger.info(f"Status endpoint called for user {user_id}")
    
    # Get the user state for this user ID
    user_state = get_user_state(user_id)
    logger.info(f"User task status: {user_state.background_task['status']}")
    
    # Dump the entire background_task dictionary for debugging
    logger.info(f"User background_task keys: {list(user_state.background_task.keys())}")
    for key, value in user_state.background_task.items():
        if isinstance(value, str) and len(value) > 100:
            logger.info(f"User background_task[{key}] = {value[:100]}...")
        else:
            logger.info(f"User background_task[{key}] = {value}")
    
    # Get feedback state from web_feedback module
    feedback_state = get_web_feedback_user_state(user_id)
    
    # Check specifically for draft email in current user's state
    has_draft = "draft_email" in user_state.background_task and user_state.background_task["draft_email"] is not None
    logger.info(f"Draft email present for current user: {has_draft}")
    
    # If no draft is found directly in the user state, try to extract it from the results
    draft_email = user_state.background_task.get("draft_email")
    draft_subject = user_state.background_task.get("draft_subject")
    draft_recipient = user_state.background_task.get("draft_recipient")
    
    if not draft_email and "results" in user_state.background_task:
        # Try to extract draft email using our robust function
        extracted_email, extracted_subject, extracted_recipient = extract_draft_email_data(user_state.background_task["results"])
        if extracted_email:
            logger.info("Found draft email using extraction function for status endpoint")
            draft_email = extracted_email
            draft_subject = extracted_subject
            draft_recipient = extracted_recipient
            has_draft = True
    
    if has_draft:
        logger.info(f"Draft subject: {draft_subject or 'None'}")
        logger.info(f"Draft recipient: {draft_recipient or 'None'}")
        logger.info(f"Draft email length: {len(draft_email)}")
    
    # Construct the response 
    response = {
        "running": user_state.background_task["running"],
        "status": user_state.background_task["status"],
        "results": user_state.background_task["results"],
        "feedback_required": feedback_state.waiting_for_feedback,
        "current_prompt": feedback_state.current_prompt,
        "current_decision": feedback_state.current_decision,
        "current_context": str(feedback_state.current_context) if feedback_state.current_context else None,
        "draft_email": draft_email,
        "draft_subject": draft_subject,
        "draft_recipient": draft_recipient
    }
    
    # Log the draft fields in the response
    logger.info(f"Status response has draft email: {'Yes' if response.get('draft_email') else 'No'}")
    if response.get('draft_email'):
        logger.info(f"Response draft email length: {len(response['draft_email'])}")
    
    return response

@app.post("/provide-feedback")
async def provide_feedback_endpoint(feedback_request: FeedbackRequest, request: Request):
    """Endpoint to provide feedback to the running process."""
    # Get current user ID
    user_id = await get_current_user_id(request)
    
    # Use the web_feedback module's provide_feedback function
    success = provide_feedback(user_id, feedback_request.feedback)
    
    if not success:
        raise HTTPException(status_code=400, detail="No feedback is currently requested for this user.")
    
    return {"status": "success", "message": "Feedback provided successfully."}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    # Get user ID from session cookie
    session_cookie = websocket.cookies.get("session")
    
    if not session_cookie:
        # If no session cookie, create a temporary user ID
        user_id = str(uuid.uuid4())
        logger.warning(f"No session cookie found, creating temporary user ID: {user_id}")
    else:
        # Try to extract the user ID from the session cookie
        try:
            from itsdangerous import URLSafeSerializer
            serializer = URLSafeSerializer(SESSION_SECRET_KEY)
            try:
                session_data = serializer.loads(session_cookie)
                user_id = session_data.get("user_id", str(uuid.uuid4()))
                logger.info(f"Retrieved user ID from session: {user_id}")
            except Exception as e:
                logger.error(f"Error decoding session cookie: {str(e)}")
                user_id = str(uuid.uuid4())
                logger.info(f"Created new user ID due to session decode error: {user_id}")
        except Exception as e:
            logger.error(f"Error extracting user ID from session: {str(e)}")
            user_id = str(uuid.uuid4())
            logger.info(f"Created new user ID due to exception: {user_id}")
    
    # Store this user ID globally for other endpoints to use
    global LAST_CONNECTED_USER_ID
    LAST_CONNECTED_USER_ID = user_id
    logger.info(f"Updated LAST_CONNECTED_USER_ID to {user_id}")
    
    # Create user state if it doesn't exist
    user_state = get_user_state(user_id)
    
    # Connect the WebSocket with the user ID
    await manager.connect(websocket, user_id)
    
    # Set this as the current user ID in the web_feedback module
    set_current_user_id(user_id)
    
    try:
        # Send initial status to this user only
        await websocket.send_json({
            'type': 'status_update',
            'status': user_state.background_task["status"],
            'results': user_state.background_task["results"]
        })
        
        # Check if there's a pending feedback request for this user or any user
        feedback_state = get_web_feedback_user_state(user_id)
        
        # SECURITY FIX: Removed code that transferred feedback requests between users
        # Each user should only see their own feedback requests
        
        if feedback_state.waiting_for_feedback:
            # Format context as string if needed
            context_str = None
            if feedback_state.current_context:
                if isinstance(feedback_state.current_context, dict):
                    context_str = "\n".join([f"{k}: {v}" for k, v in feedback_state.current_context.items()])
                else:
                    context_str = str(feedback_state.current_context)
            
            logger.info(f"Sending pending feedback request to user {user_id}")
            await websocket.send_json({
                'type': 'feedback_required',
                'prompt': feedback_state.current_prompt,
                'decision': feedback_state.current_decision,
                'context': context_str
            })
        
        # Handle incoming messages
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'provide_feedback':
                # Use the web_feedback module's provide_feedback function
                success = provide_feedback(user_id, data.get('feedback', True))
                
                if success:
                    await websocket.send_json({
                        'type': 'feedback_received',
                        'status': 'success'
                    })
                else:
                    await websocket.send_json({
                        'type': 'feedback_error',
                        'status': 'error',
                        'message': 'No feedback is currently requested'
                    })
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for user {user_id}")

@app.get("/debug/simulate-draft")
async def simulate_draft(request: Request, user_id: Optional[str] = None):
    """Debug endpoint to simulate a draft email for the current user."""
    # Get current user ID if not provided
    if not user_id:
        user_id = await get_current_user_id(request)
    
    logger.info(f"Simulating draft email for user {user_id}")
    
    # Get user state explicitly
    user_state = get_user_state(user_id)
    
    # Set draft email data
    user_state.background_task["draft_email"] = "This is a simulated draft email for testing.\n\nIt contains multiple paragraphs to test the formatting.\n\nBest regards,\nTest System"
    user_state.background_task["draft_subject"] = "Test Draft Email"
    user_state.background_task["draft_recipient"] = "test@example.com"
    user_state.background_task["status"] = "completed"
    
    logger.info("Draft email set in user state:")
    logger.info(f"Draft email length: {len(user_state.background_task['draft_email'])}")
    logger.info(f"Draft subject: {user_state.background_task['draft_subject']}")
    logger.info(f"Draft recipient: {user_state.background_task['draft_recipient']}")
    
    # Verify user state was updated
    logger.info(f"Verifying user state after update for user {user_id}")
    updated_state = get_user_state(user_id)
    logger.info(f"User state has draft email: {'draft_email' in updated_state.background_task}")
    if 'draft_email' in updated_state.background_task:
        logger.info(f"Draft email in updated state length: {len(updated_state.background_task['draft_email'])}")
    
    # Update the global user ID if it's different
    global LAST_CONNECTED_USER_ID
    if user_id != LAST_CONNECTED_USER_ID:
        logger.info(f"Updating global user ID from {LAST_CONNECTED_USER_ID} to {user_id}")
        LAST_CONNECTED_USER_ID = user_id
    
    # Send update to the user via WebSocket if they have a connection
    def send_status_update():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        status_data = {
            'type': 'status_update',
            'status': "completed",
            'results': "Simulated draft created",
            'draft_email': user_state.background_task["draft_email"],
            'draft_subject': user_state.background_task["draft_subject"],
            'draft_recipient': user_state.background_task["draft_recipient"]
        }
        
        # Check if user has a WebSocket connection
        has_connection = False
        if hasattr(manager, 'user_connections') and user_id in manager.user_connections:
            has_connection = True
        
        logger.info(f"User {user_id} has WebSocket connection: {has_connection}")
        
        if has_connection:
            logger.info(f"Sending simulated draft to user {user_id} via WebSocket")
            loop.run_until_complete(
                manager.send_to_user(user_id, status_data)
            )
            logger.info(f"WebSocket update sent to user {user_id}")
        else:
            logger.info(f"No WebSocket connection for user {user_id}, not sending update")
            # SECURITY FIX: Removed broadcast to all users to prevent data leakage
            logger.warning(f"Not broadcasting draft email to other users for security reasons")
    
    threading.Thread(target=send_status_update).start()
    
    return JSONResponse({
        "status": "success",
        "message": "Simulated draft email created. Check the UI to see it.",
        "draft_email_length": len(user_state.background_task["draft_email"]),
        "user_id": user_id
    })

@app.get("/debug/session")
async def debug_session(request: Request):
    """Debug endpoint to inspect the session for the current request."""
    # Get session data
    session_data = dict(request.session)
    user_id = session_data.get("user_id", "none")
    
    # Check global ID
    global LAST_CONNECTED_USER_ID
    
    # List all users in the state
    all_users = list(user_states.keys())
    
    # Dump info about connections
    ws_connections = {}
    if hasattr(manager, 'user_connections'):
        for uid, connections in manager.user_connections.items():
            ws_connections[uid] = len(connections)
    
    return JSONResponse({
        "session_user_id": user_id,
        "global_user_id": LAST_CONNECTED_USER_ID,
        "all_users": all_users,
        "websocket_connections": ws_connections
    })

@app.get("/debug/simulate-draft-for-all")
async def simulate_draft_for_all(request: Request):
    """Debug endpoint that was previously insecure - now just creates a draft for current user."""
    # Get current user ID
    user_id = await get_current_user_id(request)
    logger.info(f"simulate-draft-for-all called, but only creating draft for current user {user_id}")
    
    # Get user state
    user_state = get_user_state(user_id)
    
    # Set draft email data
    user_state.background_task["draft_email"] = f"This is a simulated draft email for user {user_id}.\n\nIt contains multiple paragraphs to test the formatting.\n\nBest regards,\nTest System"
    user_state.background_task["draft_subject"] = "Test Draft Email"
    user_state.background_task["draft_recipient"] = "test@example.com"
    user_state.background_task["status"] = "completed"
    
    # Log the update
    logger.info(f"Updated draft for user {user_id}")
    
    # Send update to the user via WebSocket
    def send_status_update():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        status_data = {
            'type': 'status_update',
            'status': "completed",
            'results': "Simulated draft created",
            'draft_email': user_state.background_task["draft_email"],
            'draft_subject': user_state.background_task["draft_subject"],
            'draft_recipient': user_state.background_task["draft_recipient"]
        }
        
        logger.info(f"Sending simulated draft to user {user_id} via WebSocket")
        
        loop.run_until_complete(
            manager.send_to_user(user_id, status_data)
        )
    
    # Start a thread
    thread = threading.Thread(target=send_status_update)
    thread.daemon = True
    thread.start()
    
    return JSONResponse({
        "status": "success",
        "message": "Simulated draft email created only for the current user.",
        "user_id": user_id,
        "draft_email_length": len(user_state.background_task["draft_email"])
    })

@app.get("/debug/simulate-orchestrator-response")
async def simulate_orchestrator_response(request: Request):
    """Debug endpoint to simulate the exact response structure from the orchestrator."""
    # Get current user ID
    user_id = await get_current_user_id(request)
    logger.info(f"Simulating orchestrator response for user {user_id}")
    
    # Create a response dictionary that matches the structure from orchestrator
    orchestrator_response = {
        "summary": "Processed 1 emails. Responded to 1 and archived 0.",
        "draft_email": "This is a simulated draft email created to match the orchestrator's exact response structure.\n\nIt contains multiple paragraphs to test the formatting.\n\nBest regards,\nTest System",
        "draft_subject": "Test Orchestrator Response",
        "draft_recipient": "test@example.com",
        "draft_id": "simulated-id-123",
        "details": {
            "emails_processed": 1,
            "emails_responded": 1,
            "emails_archived": 0,
            "latest_draft": {
                "draft_email": "This is the same email in the nested structure.",
                "draft_subject": "Test Orchestrator Response",
                "draft_recipient": "test@example.com",
                "draft_id": "simulated-id-123"
            }
        }
    }
    
    # Get user state
    user_state = get_user_state(user_id)
    
    # Store the orchestrator response in the user state
    user_state.background_task["results"] = orchestrator_response
    user_state.background_task["draft_email"] = orchestrator_response["draft_email"]
    user_state.background_task["draft_subject"] = orchestrator_response["draft_subject"]
    user_state.background_task["draft_recipient"] = orchestrator_response["draft_recipient"]
    user_state.background_task["status"] = "completed"
    
    # Log what we've stored
    logger.info(f"Stored orchestrator response in user state:")
    logger.info(f"draft_email length: {len(user_state.background_task['draft_email'])}")
    logger.info(f"draft_subject: {user_state.background_task['draft_subject']}")
    logger.info(f"draft_recipient: {user_state.background_task['draft_recipient']}")
    
    # Send update to the user via WebSocket
    def send_status_update():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        status_data = {
            'type': 'status_update',
            'status': "completed",
            'results': orchestrator_response,
            'draft_email': user_state.background_task["draft_email"],
            'draft_subject': user_state.background_task["draft_subject"],
            'draft_recipient': user_state.background_task["draft_recipient"]
        }
        
        # Log what we're sending
        logger.info(f"Sending status update with keys: {list(status_data.keys())}")
        logger.info(f"Status update has draft_email: {status_data.get('draft_email') is not None}")
        
        if status_data.get('draft_email'):
            logger.info(f"Draft email length in status: {len(status_data['draft_email'])}")
        
        # Check if user has a WebSocket connection
        has_connection = False
        if hasattr(manager, 'user_connections') and user_id in manager.user_connections:
            has_connection = True
            logger.info(f"User {user_id} has {len(manager.user_connections[user_id])} WebSocket connection(s)")
        
        if has_connection:
            loop.run_until_complete(
                manager.send_to_user(user_id, status_data)
            )
            logger.info(f"Sent status update to user {user_id}")
        else:
            logger.info(f"No WebSocket connection for user {user_id}")
    
    # Start a thread to send the update
    thread = threading.Thread(target=send_status_update)
    thread.daemon = True
    thread.start()
    
    return JSONResponse({
        "status": "success",
        "message": "Simulated orchestrator response. Check the UI to see the draft.",
        "orchestrator_response": orchestrator_response
    })

if __name__ == "__main__":
    # Run the server with access logs disabled
    uvicorn.run(
        "fastapi_server:app", 
        host="0.0.0.0", 
        port=8000, 
        reload=True,
        log_level="warning",
        access_log=False      # Disable access logs completely
    ) 