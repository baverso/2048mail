import logging
import asyncio
import threading
from typing import Optional, Dict, List
from fastapi import APIRouter, Request, Query
from fastapi.responses import JSONResponse

from devserver.services.user_state_service import user_state_service
from devserver.services.feedback_service import feedback_service
from devserver.websockets.connection_manager import connection_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/debug", tags=["debug"])


@router.get("/simulate-draft")
async def simulate_draft(request: Request, user_id: Optional[str] = None):
    """
    Debug endpoint to simulate a draft email for the current user.
    """
    # Get current user ID if not provided
    if not user_id:
        user_id = await user_state_service.get_current_user_id(request)
    
    logger.info(f"Simulating draft email for user {user_id}")
    
    # Get user state explicitly
    user_state = user_state_service.get_user_state(user_id)
    
    # Set draft email data
    user_state.background_task.draft_email = "This is a simulated draft email for testing.\n\nIt contains multiple paragraphs to test the formatting.\n\nBest regards,\nTest System"
    user_state.background_task.draft_subject = "Test Draft Email"
    user_state.background_task.draft_recipient = "test@example.com"
    user_state.background_task.status = "completed"
    
    logger.info("Draft email set in user state:")
    logger.info(f"Draft email length: {len(user_state.background_task.draft_email)}")
    logger.info(f"Draft subject: {user_state.background_task.draft_subject}")
    logger.info(f"Draft recipient: {user_state.background_task.draft_recipient}")
    
    # Verify user state was updated
    logger.info(f"Verifying user state after update for user {user_id}")
    updated_state = user_state_service.get_user_state(user_id)
    logger.info(f"User state has draft email: {updated_state.background_task.draft_email is not None}")
    if updated_state.background_task.draft_email:
        logger.info(f"Draft email in updated state length: {len(updated_state.background_task.draft_email)}")
    
    # Update the global user ID if it's different
    last_connected_user_id = user_state_service.get_last_connected_user_id()
    if user_id != last_connected_user_id:
        logger.info(f"Updating global user ID from {last_connected_user_id} to {user_id}")
        user_state_service.set_last_connected_user_id(user_id)
    
    # Send update to the user via WebSocket if they have a connection
    def send_status_update():
        asyncio.set_event_loop(asyncio.new_event_loop())
        
        status_data = {
            'type': 'status_update',
            'status': "completed",
            'results': "Simulated draft created",
            'draft_email': user_state.background_task.draft_email,
            'draft_subject': user_state.background_task.draft_subject,
            'draft_recipient': user_state.background_task.draft_recipient
        }
        
        # Check if user has a WebSocket connection
        has_connection = False
        if hasattr(connection_manager, 'user_connections') and user_id in connection_manager.user_connections:
            has_connection = True
        
        logger.info(f"User {user_id} has WebSocket connection: {has_connection}")
        
        if has_connection:
            logger.info(f"Sending simulated draft to user {user_id} via WebSocket")
            asyncio.get_event_loop().run_until_complete(
                connection_manager.send_to_user(user_id, status_data)
            )
            logger.info(f"WebSocket update sent to user {user_id}")
        else:
            logger.info(f"No WebSocket connection for user {user_id}, not sending update")
    
    threading.Thread(target=send_status_update).start()
    
    return JSONResponse({
        "status": "success",
        "message": "Simulated draft email created. Check the UI to see it.",
        "draft_email_length": len(user_state.background_task.draft_email),
        "user_id": user_id
    })


@router.get("/session")
async def debug_session(request: Request):
    """
    Debug endpoint to inspect the session for the current request.
    """
    # Get session data
    session_data = dict(request.session)
    user_id = session_data.get("user_id", "none")
    
    # Check global ID
    last_connected_user_id = user_state_service.get_last_connected_user_id()
    
    # List all users in the state
    all_users = list(user_state_service._user_states.keys())
    
    # Dump info about connections
    ws_connections = {}
    if hasattr(connection_manager, 'user_connections'):
        for uid, connections in connection_manager.user_connections.items():
            ws_connections[uid] = len(connections)
    
    return JSONResponse({
        "session_user_id": user_id,
        "global_user_id": last_connected_user_id,
        "all_users": all_users,
        "websocket_connections": ws_connections
    })


@router.get("/simulate-orchestrator-response")
async def simulate_orchestrator_response(request: Request):
    """
    Debug endpoint to simulate the exact response structure from the orchestrator.
    """
    # Get current user ID
    user_id = await user_state_service.get_current_user_id(request)
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
    user_state = user_state_service.get_user_state(user_id)
    
    # Store the orchestrator response in the user state
    user_state.background_task.results = orchestrator_response
    user_state.background_task.draft_email = orchestrator_response["draft_email"]
    user_state.background_task.draft_subject = orchestrator_response["draft_subject"]
    user_state.background_task.draft_recipient = orchestrator_response["draft_recipient"]
    user_state.background_task.status = "completed"
    
    # Log what we've stored
    logger.info(f"Stored orchestrator response in user state:")
    logger.info(f"draft_email length: {len(user_state.background_task.draft_email)}")
    logger.info(f"draft_subject: {user_state.background_task.draft_subject}")
    logger.info(f"draft_recipient: {user_state.background_task.draft_recipient}")
    
    # Send update to the user via WebSocket
    def send_status_update():
        asyncio.set_event_loop(asyncio.new_event_loop())
        
        status_data = {
            'type': 'status_update',
            'status': "completed",
            'results': orchestrator_response,
            'draft_email': user_state.background_task.draft_email,
            'draft_subject': user_state.background_task.draft_subject,
            'draft_recipient': user_state.background_task.draft_recipient
        }
        
        # Log what we're sending
        logger.info(f"Sending status update with keys: {list(status_data.keys())}")
        logger.info(f"Status update has draft_email: {status_data.get('draft_email') is not None}")
        
        if status_data.get('draft_email'):
            logger.info(f"Draft email length in status: {len(status_data['draft_email'])}")
        
        # Check if user has a WebSocket connection
        has_connection = False
        if hasattr(connection_manager, 'user_connections') and user_id in connection_manager.user_connections:
            has_connection = True
            logger.info(f"User {user_id} has {len(connection_manager.user_connections[user_id])} WebSocket connection(s)")
        
        if has_connection:
            asyncio.get_event_loop().run_until_complete(
                connection_manager.send_to_user(user_id, status_data)
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