#!/usr/bin/env python3
"""
web_feedback.py

This module provides functions for collecting human feedback during the email processing workflow
via a web interface using WebSockets. It replaces the CLI-based feedback mechanism with a properly
isolated web-based solution that maintains user-specific feedback queues.

Author: Brett Averso
Date: April 2, 2024
License: GPL-3.0
"""

import logging
import queue
import threading
import time
from typing import Dict, Any, Optional, Tuple, List

# Configure logging
logger = logging.getLogger(__name__)

# Global state for webserver communication
_connection_manager = None
_user_feedback_states = {}
_current_user_id = None  # Global tracker for current user ID

class UserFeedbackState:
    """
    Maintains the state of feedback requests for a specific user.
    """
    def __init__(self):
        self.feedback_queue = queue.Queue()
        self.waiting_for_feedback = False
        self.current_prompt = None
        self.current_decision = None
        self.current_context = None
        self.timeout = 300  # Default timeout in seconds
        
    def reset(self):
        """Reset the state after feedback is received or timeout occurs."""
        self.waiting_for_feedback = False
        self.current_prompt = None
        self.current_decision = None
        self.current_context = None
        
        # Clear the queue to prevent stale feedback
        while not self.feedback_queue.empty():
            try:
                self.feedback_queue.get_nowait()
            except queue.Empty:
                break

def register_connection_manager(manager):
    """
    Register the FastAPI WebSocket connection manager with this module.
    
    Args:
        manager: The ConnectionManager instance from fastapi_server.py
    """
    global _connection_manager
    _connection_manager = manager
    logger.info("WebSocket connection manager registered with web_feedback module")

def set_current_user_id(user_id: str):
    """
    Set the current user ID for feedback requests.
    
    Args:
        user_id (str): The user ID to use for feedback requests
    """
    global _current_user_id
    previous_id = _current_user_id
    _current_user_id = user_id
    logger.info(f"Set current user ID for feedback to: {user_id} (previous: {previous_id})")
    
    # Log all active connections for debugging
    if _connection_manager:
        connections = getattr(_connection_manager, 'user_connections', {})
        active_users = list(connections.keys())
        logger.info(f"Active WebSocket connections: {active_users}")

def get_current_user_id() -> Optional[str]:
    """
    Get the current user ID for feedback requests.
    
    Returns:
        Optional[str]: The current user ID, or None if not set
    """
    return _current_user_id

def list_active_connections():
    """
    Log information about all active connections
    """
    if _connection_manager:
        connections = getattr(_connection_manager, 'user_connections', {})
        for user_id, sockets in connections.items():
            logger.info(f"User {user_id}: {len(sockets)} active connections")
    else:
        logger.warning("No connection manager available")

def get_user_state(user_id: str) -> UserFeedbackState:
    """
    Get or create a user feedback state object for the given user ID.
    
    Args:
        user_id (str): The unique identifier for the user
        
    Returns:
        UserFeedbackState: The user's feedback state object
    """
    if user_id not in _user_feedback_states:
        _user_feedback_states[user_id] = UserFeedbackState()
    return _user_feedback_states[user_id]

def get_yes_no_feedback(prompt: Optional[str] = None, 
                        decision: Optional[str] = None, 
                        context: Optional[Any] = None, 
                        user_id: Optional[str] = None,
                        timeout: int = 300) -> Tuple[bool, str]:
    """
    Get yes/no feedback from a human user via the web interface.
    
    Args:
        prompt (str, optional): The question to ask the user.
        decision (str, optional): The AI's decision that is being validated.
        context (Any, optional): Additional context to display to the user.
        user_id (str, optional): The user ID to send the feedback request to.
        timeout (int, optional): Timeout in seconds for waiting for feedback.
        
    Returns:
        tuple: (is_correct, "correct"/"wrong") where:
            - is_correct (bool): True if the human agrees with the AI decision, False otherwise.
            - human_input (str): The raw input from the human ('correct' or 'wrong').
    """
    if not _connection_manager:
        logger.error("WebSocket connection manager not registered with web_feedback module")
        return True, "correct"  # Default to yes if no connection manager
    
    # Log all active connections for debugging
    list_active_connections()
    
    # Use the explicitly set current user ID if available and no user_id was provided
    if user_id is None:
        user_id = get_current_user_id()
        if user_id:
            logger.info(f"Using current user ID for feedback: {user_id}")
        else:
            # Try to detect the user ID from the current thread
            from threading import current_thread
            thread_name = current_thread().name
            
            # Find which user's task is running in this thread
            for uid, state in _user_feedback_states.items():
                thread_info = getattr(state, 'thread_name', None)
                if thread_info == thread_name:
                    user_id = uid
                    break
                    
            if not user_id:
                logger.warning("Could not determine user for feedback request, using default behavior")
                return True, "correct"  # Default to yes if we can't determine the user
    
    # Check if the user has an active WebSocket connection
    connections = getattr(_connection_manager, 'user_connections', {})
    if user_id not in connections:
        logger.warning(f"No active WebSocket connections for user {user_id}, checking for single connection")
        
        # If there's only one user connected, use that user instead
        if len(connections) == 1:
            connected_user_id = next(iter(connections.keys()))
            logger.info(f"Found only one connected user ({connected_user_id}), using that instead of {user_id}")
            user_id = connected_user_id
            # Update the current user ID
            set_current_user_id(user_id)
        else:
            logger.error(f"Multiple users connected ({list(connections.keys())}), but none match request for {user_id}")
            return True, "correct"  # Default to yes if no connection for this user
    
    # Format the prompt if not provided
    if prompt is None:
        if decision == "respond":
            prompt = "I think we should respond."
        elif decision == "no response needed":
            prompt = "This email does not need a response."
        elif decision == "decline":
            prompt = "I think we should politely decline."
        elif decision == "move forward":
            prompt = "I think we should draft a response."
        elif decision == "schedule meeting":
            prompt = "I think we should setup a meeting."
        elif decision == "yes":
            prompt = "This is a meeting request that needs scheduling."
        elif decision == "no":
            prompt = "This is not just a meeting request and needs a full response."
        else:
            prompt = f"The AI has decided: {decision}"
    
    # Get the user's feedback state
    user_state = get_user_state(user_id)
    
    # Set the current feedback request
    user_state.waiting_for_feedback = True
    user_state.current_prompt = prompt
    user_state.current_decision = decision
    user_state.current_context = context
    user_state.timeout = timeout
    
    # Store thread name for later identification
    user_state.thread_name = threading.current_thread().name
    
    # Send feedback request to the specific user through WebSocket
    def send_feedback_request():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Format context as string if needed
        context_str = None
        if context:
            if isinstance(context, dict):
                # Format dictionary in a more readable way
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
            else:
                context_str = str(context)
                
        logger.info(f"Sending feedback request to user {user_id} with prompt: '{prompt}'")
        loop.run_until_complete(
            _connection_manager.send_to_user(user_id, {
                'type': 'feedback_required',
                'prompt': prompt,
                'decision': decision,
                'context': context_str
            })
        )
        loop.close()
    
    # Start a thread to send the feedback request
    threading.Thread(target=send_feedback_request).start()
    
    logger.info(f"Waiting for feedback from user {user_id}...")
    
    # Wait for feedback from the user's queue
    try:
        feedback_result = user_state.feedback_queue.get(timeout=timeout)
        is_correct = feedback_result.get('feedback', True)
        human_input = "correct" if is_correct else "wrong"
        
        if decision:
            if is_correct:
                logger.info(f"Human confirmed AI decision: {decision}")
            else:
                logger.info(f"Human overrode AI decision: {decision}")
        
        # Reset the state
        user_state.reset()
        
        return is_correct, human_input
    except queue.Empty:
        logger.warning(f"Timed out waiting for feedback from user {user_id}")
        
        # Send timeout notification
        def send_timeout_notification():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(
                _connection_manager.send_to_user(user_id, {
                    'type': 'feedback_timeout',
                    'message': f"Feedback request timed out after {timeout} seconds. Proceeding with default action."
                })
            )
            loop.close()
        
        threading.Thread(target=send_timeout_notification).start()
        
        # Reset the state
        user_state.reset()
        
        return True, "correct"  # Default to yes if timeout

def provide_feedback(user_id: str, feedback: bool) -> bool:
    """
    Process incoming feedback from the user through the web interface.
    
    Args:
        user_id (str): The user ID providing the feedback
        feedback (bool): True for 'correct', False for 'wrong'
        
    Returns:
        bool: True if feedback was successfully provided, False otherwise
    """
    if user_id not in _user_feedback_states:
        logger.warning(f"Received feedback for unknown user: {user_id}")
        
        # If there's only one user with feedback waiting, use that one
        waiting_users = [uid for uid, state in _user_feedback_states.items() if state.waiting_for_feedback]
        if len(waiting_users) == 1:
            correct_user_id = waiting_users[0]
            logger.info(f"Found one user waiting for feedback ({correct_user_id}), using that instead of {user_id}")
            user_id = correct_user_id
        else:
            return False
        
    user_state = _user_feedback_states[user_id]
    
    if not user_state.waiting_for_feedback:
        logger.warning(f"Received feedback when none was requested for user: {user_id}")
        return False
    
    # Put the feedback in the user's queue
    user_state.feedback_queue.put({'feedback': feedback})
    logger.info(f"Provided feedback for user {user_id}: {'correct' if feedback else 'wrong'}")
    
    # Notify the user that their feedback was received
    def send_feedback_confirmation():
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(
            _connection_manager.send_to_user(user_id, {
                'type': 'feedback_received',
                'status': 'success'
            })
        )
        loop.close()
    
    threading.Thread(target=send_feedback_confirmation).start()
    
    return True

def get_feedback_with_options(prompt: str, options: List[str], context: Optional[Any] = None, 
                              user_id: Optional[str] = None, timeout: int = 300) -> str:
    """
    Get feedback from a human user with multiple options via the web interface.
    
    Args:
        prompt (str): The question to ask the user.
        options (list): List of valid options the user can choose from.
        context (Any, optional): Additional context to display to the user.
        user_id (str, optional): The user ID to send the feedback request to.
        timeout (int, optional): Timeout in seconds for waiting for feedback.
        
    Returns:
        str: The selected option, or the first option if timeout or error occurs.
    """
    # If user_id is not provided, use the current user ID
    if user_id is None:
        user_id = get_current_user_id()
    
    # TODO: Implement multi-option feedback if needed
    logger.warning("Multi-option feedback not yet implemented in web interface")
    return options[0]  # Return the first option as default 