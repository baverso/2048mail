from typing import Dict, Optional, Any
import logging
from dataclasses import dataclass

from tools.web_feedback import (
    register_connection_manager, 
    provide_feedback as original_provide_feedback, 
    get_user_state as get_web_feedback_user_state, 
    set_current_user_id
)

logger = logging.getLogger(__name__)

@dataclass
class FeedbackState:
    """State tracking for user feedback."""
    waiting_for_feedback: bool = False
    current_prompt: Optional[str] = None
    current_decision: Optional[str] = None
    current_context: Optional[Any] = None


class FeedbackService:
    """Service for handling user feedback."""
    
    def __init__(self):
        # Dictionary to store feedback states by user ID
        self._feedback_states: Dict[str, FeedbackState] = {}
        
    def get_feedback_state(self, user_id: str) -> FeedbackState:
        """
        Get the feedback state for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Feedback state for the user
        """
        # Get from tools.web_feedback if possible
        original_state = get_web_feedback_user_state(user_id)
        
        # If not in our local dict, initialize it
        if user_id not in self._feedback_states:
            self._feedback_states[user_id] = FeedbackState()
            
        # Update our state from the original state
        if original_state is not None:
            self._feedback_states[user_id].waiting_for_feedback = original_state.waiting_for_feedback
            self._feedback_states[user_id].current_prompt = original_state.current_prompt
            self._feedback_states[user_id].current_decision = original_state.current_decision
            self._feedback_states[user_id].current_context = original_state.current_context
            
        return self._feedback_states[user_id]
    
    def provide_feedback(self, user_id: str, feedback: bool) -> bool:
        """
        Provide feedback for a user.
        
        Args:
            user_id: ID of the user providing feedback
            feedback: The feedback value
            
        Returns:
            True if feedback was successfully provided, False otherwise
        """
        logger.info(f"Providing feedback for user {user_id}: {feedback}")
        
        # Set the current user ID in the web_feedback module
        set_current_user_id(user_id)
        
        # Use the original provide_feedback function
        result = original_provide_feedback(user_id, feedback)
        
        # Update our local state
        feedback_state = self.get_feedback_state(user_id)
        if result:
            feedback_state.waiting_for_feedback = False
        
        return result
    
    def set_connection_manager(self, manager):
        """
        Set the connection manager for the feedback service.
        
        Args:
            manager: Connection manager instance
        """
        register_connection_manager(manager)
        logger.info("Registered connection manager with web_feedback module")
    
    def set_current_user(self, user_id: str):
        """
        Set the current user ID for feedback purposes.
        
        Args:
            user_id: ID of the current user
        """
        set_current_user_id(user_id)
        logger.info(f"Set current user ID for feedback: {user_id}")


# Singleton instance of the FeedbackService
feedback_service = FeedbackService() 