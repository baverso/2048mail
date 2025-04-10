import logging
import uuid
from typing import Optional, Dict, Any
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Cookie

from devserver.websockets.connection_manager import connection_manager
from devserver.services.feedback_service import feedback_service
from devserver.services.user_state_service import user_state_service
from devserver.models.api_models import (
    FeedbackMessage, FeedbackReceived, FeedbackRequired, StatusUpdate
)
from devserver.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


async def get_user_id_from_session(session: Optional[str] = Cookie(None)) -> str:
    """
    Extract user ID from session cookie.
    
    Args:
        session: Session cookie
        
    Returns:
        User ID
    """
    if not session:
        # If no session cookie, create a temporary user ID
        user_id = str(uuid.uuid4())
        logger.warning(f"No session cookie found, creating temporary user ID: {user_id}")
        return user_id
    
    # Try to extract the user ID from the session cookie
    try:
        from itsdangerous import URLSafeSerializer
        serializer = URLSafeSerializer(settings.SESSION_SECRET_KEY)
        
        try:
            session_data = serializer.loads(session)
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

    return user_id


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    user_id: str = Depends(get_user_id_from_session)
):
    """
    WebSocket endpoint for real-time communication with clients.
    
    Args:
        websocket: WebSocket connection
        user_id: ID of the user making the connection
    """
    # Store this user ID globally for other endpoints to use
    user_state_service.set_last_connected_user_id(user_id)
    logger.info(f"Updated last connected user ID to {user_id}")
    
    # Create user state if it doesn't exist
    user_state = user_state_service.get_user_state(user_id)
    
    # Connect the WebSocket with the user ID
    await connection_manager.connect(websocket, user_id)
    
    # Set this as the current user ID in the feedback service
    feedback_service.set_current_user(user_id)
    
    try:
        # Send initial status to this user only
        await websocket.send_json(StatusUpdate(
            status=user_state.background_task.status,
            results=user_state.background_task.results
        ).dict())
        
        # Check if there's a pending feedback request for this user
        feedback_state = feedback_service.get_feedback_state(user_id)
        
        if feedback_state.waiting_for_feedback:
            # Format context as string if needed
            context_str = None
            if feedback_state.current_context:
                if isinstance(feedback_state.current_context, dict):
                    context_str = "\n".join([f"{k}: {v}" for k, v in feedback_state.current_context.items()])
                else:
                    context_str = str(feedback_state.current_context)
            
            logger.info(f"Sending pending feedback request to user {user_id}")
            await websocket.send_json(FeedbackRequired(
                prompt=feedback_state.current_prompt or "Provide feedback:",
                decision=feedback_state.current_decision,
                context=context_str
            ).dict())
        
        # Handle incoming messages
        while True:
            raw_data = await websocket.receive_json()
            
            # Try to parse as FeedbackMessage
            try:
                data = FeedbackMessage(**raw_data)
                if data.type == "provide_feedback":
                    # Use the feedback service to provide feedback
                    success = feedback_service.provide_feedback(user_id, data.feedback)
                    
                    if success:
                        await websocket.send_json(FeedbackReceived().dict())
                    else:
                        await websocket.send_json({
                            'type': 'feedback_error',
                            'status': 'error',
                            'message': 'No feedback is currently requested'
                        })
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {str(e)}")
                await websocket.send_json({
                    'type': 'error',
                    'message': f"Invalid message format: {str(e)}"
                })
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
        logger.info(f"WebSocket disconnected for user {user_id}") 