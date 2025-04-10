import logging
import threading
import asyncio
from typing import Dict, Any
from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.responses import JSONResponse

from devserver.services.oauth_service import (
    OAuthServiceInterface, 
    get_oauth_service, 
    is_authenticated
)
from devserver.services.user_state_service import user_state_service
from devserver.services.email_service import email_service
from devserver.services.feedback_service import feedback_service
from devserver.websockets.connection_manager import connection_manager
from devserver.models.api_models import FeedbackRequest, StatusResponse, ProcessEmailsResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/process-emails", response_model=ProcessEmailsResponse)
async def process_emails(
    request: Request,
    oauth_service: OAuthServiceInterface = Depends(get_oauth_service)
):
    """
    Start processing emails in the background.
    """
    # Get current user ID
    user_id = await user_state_service.get_current_user_id(request)
    logger.info(f"Process-emails endpoint called by user {user_id}")
    
    user_state = user_state_service.get_user_state(user_id)
    
    # Check if already running
    if user_state.background_task.running:
        logger.info(f"Email processing is already running for user {user_id}")
        return ProcessEmailsResponse(
            status="already_running",
            message="Email processing is already running."
        )
    
    # Check authentication
    creds = oauth_service.get_credentials()
    if not creds or not creds.valid:
        logger.info(f"User {user_id} is not authenticated, cannot process emails")
        return ProcessEmailsResponse(
            status="not_authenticated",
            message="You need to authenticate first."
        )
    
    # Use the last connected WebSocket user ID if available
    last_connected_user_id = user_state_service.get_last_connected_user_id()
    if last_connected_user_id:
        logger.info(f"Using last connected WebSocket user ID: {last_connected_user_id} instead of session user ID: {user_id}")
        user_id = last_connected_user_id
    
    # Set the current user ID in the feedback service
    feedback_service.set_current_user(user_id)
    logger.info(f"Starting email processing for user: {user_id}")
    
    # Start background task
    user_state.background_task.running = True
    user_state.background_task.status = "starting"
    user_state.background_task.results = None
    user_state.background_task.user_id = user_id
    
    # Define the draft callback function
    def draft_callback(draft_data: Dict[str, Any]):
        logger.info(f"Draft callback received data with keys: {list(draft_data.keys())}")
        
        # Store the draft data in the user's state
        user_state.background_task.draft_email = draft_data.get("draft_email")
        user_state.background_task.draft_subject = draft_data.get("draft_subject")
        user_state.background_task.draft_recipient = draft_data.get("draft_recipient")
        user_state.background_task.results = draft_data
        
        logger.info(f"Stored draft in user state. Email length: {len(user_state.background_task.draft_email)}")
        
        # Send notification via WebSocket
        def send_draft_update():
            asyncio.set_event_loop(asyncio.new_event_loop())
            
            status_data = {
                'type': 'status_update',
                'status': "draft_created",
                'results': draft_data,
                'draft_email': draft_data.get("draft_email"),
                'draft_subject': draft_data.get("draft_subject"),
                'draft_recipient': draft_data.get("draft_recipient")
            }
            
            logger.info(f"Sending draft notification to user {user_id}")
            if hasattr(connection_manager, 'user_connections') and user_id in connection_manager.user_connections:
                asyncio.get_event_loop().run_until_complete(
                    connection_manager.send_to_user(user_id, status_data)
                )
                logger.info(f"Draft notification sent to user {user_id}")
            else:
                logger.warning(f"No WebSocket connection for user {user_id}, draft notification not sent")
        
        # Send the notification in a separate thread to avoid blocking
        notification_thread = threading.Thread(target=send_draft_update)
        notification_thread.daemon = True
        notification_thread.start()
    
    # Process emails asynchronously
    thread = email_service.process_emails_async(user_id, draft_callback)
    
    # Store thread information in user state
    user_state.background_task.thread_name = thread.name
    
    return ProcessEmailsResponse(
        status="started",
        message="Email processing started in the background."
    )


@router.get("/status", response_model=StatusResponse)
async def status(request: Request):
    """
    Check the status of the email processing task.
    """
    # Get current user ID
    user_id = await user_state_service.get_current_user_id(request)
    logger.info(f"Status endpoint called for user {user_id}")
    
    # Get the user state for this user ID
    user_state = user_state_service.get_user_state(user_id)
    logger.info(f"User task status: {user_state.background_task.status}")
    
    # Dump the entire background_task dictionary for debugging
    logger.info(f"User background_task keys: {list(user_state.background_task.dict().keys())}")
    for key, value in user_state.background_task.dict().items():
        if isinstance(value, str) and len(value or "") > 100:
            logger.info(f"User background_task[{key}] = {value[:100]}...")
        else:
            logger.info(f"User background_task[{key}] = {value}")
    
    # Get feedback state from feedback service
    feedback_state = feedback_service.get_feedback_state(user_id)
    
    # Check specifically for draft email in current user's state
    has_draft = user_state.background_task.draft_email is not None
    logger.info(f"Draft email present for current user: {has_draft}")
    
    # If no draft is found directly in the user state, try to extract it from the results
    draft_email = user_state.background_task.draft_email
    draft_subject = user_state.background_task.draft_subject
    draft_recipient = user_state.background_task.draft_recipient
    
    if not draft_email and user_state.background_task.results:
        # Try to extract draft email using our robust function
        draft = user_state_service.extract_draft_email_data(user_state.background_task.results)
        if draft:
            logger.info("Found draft email using extraction function for status endpoint")
            draft_email = draft.email_content
            draft_subject = draft.subject
            draft_recipient = draft.recipient
            has_draft = True
    
    if has_draft:
        logger.info(f"Draft subject: {draft_subject or 'None'}")
        logger.info(f"Draft recipient: {draft_recipient or 'None'}")
        logger.info(f"Draft email length: {len(draft_email)}")
    
    # Construct the response 
    response = StatusResponse(
        running=user_state.background_task.running,
        status=user_state.background_task.status,
        results=user_state.background_task.results,
        feedback_required=feedback_state.waiting_for_feedback,
        current_prompt=feedback_state.current_prompt,
        current_decision=feedback_state.current_decision,
        current_context=str(feedback_state.current_context) if feedback_state.current_context else None,
        draft_email=draft_email,
        draft_subject=draft_subject,
        draft_recipient=draft_recipient
    )
    
    # Log the draft fields in the response
    logger.info(f"Status response has draft email: {'Yes' if response.draft_email else 'No'}")
    if response.draft_email:
        logger.info(f"Response draft email length: {len(response.draft_email)}")
    
    return response


@router.post("/provide-feedback")
async def provide_feedback_endpoint(
    feedback_request: FeedbackRequest, 
    request: Request
):
    """
    Endpoint to provide feedback to the running process.
    """
    # Get current user ID
    user_id = await user_state_service.get_current_user_id(request)
    
    # Use the feedback service to provide feedback
    success = feedback_service.provide_feedback(user_id, feedback_request.feedback)
    
    if not success:
        raise HTTPException(status_code=400, detail="No feedback is currently requested for this user.")
    
    return {"status": "success", "message": "Feedback provided successfully."} 