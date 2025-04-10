from typing import Optional, Dict, Any, Callable
import logging
import threading
from agents.orchestrator_text_completions import orchestrate_email_response
from devserver.models.user_state import DraftEmail

logger = logging.getLogger(__name__)

class EmailService:
    """Service for processing emails and managing email-related tasks."""
    
    def process_emails_async(self, user_id: str, draft_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> threading.Thread:
        """
        Process emails asynchronously for a user.
        
        Args:
            user_id: ID of the user requesting email processing
            draft_callback: Optional callback function to receive draft emails
            
        Returns:
            The thread handling the processing
        """
        logger.info(f"Starting email processing thread for user: {user_id}")
        
        # Start background thread
        thread = threading.Thread(
            target=self._process_emails_task,
            args=(user_id, draft_callback),
            daemon=True
        )
        thread.start()
        return thread
    
    def _process_emails_task(self, user_id: str, draft_callback: Optional[Callable[[Dict[str, Any]], None]] = None):
        """
        Task function for processing emails.
        
        Args:
            user_id: ID of the user requesting email processing
            draft_callback: Optional callback function to receive draft emails
        """
        thread_name = threading.current_thread().name
        logger.info(f"Email processing thread {thread_name} started for user {user_id}")
        
        try:
            # Call the orchestrator
            logger.info(f"Calling orchestrator for user_id: {user_id}")
            results = orchestrate_email_response(user_id=user_id, draft_callback=draft_callback)
            logger.info(f"Orchestrator returned results type: {type(results)}")
            
            return results
            
        except Exception as e:
            logger.error(f"Email processing failed for user {user_id}: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return str(e)


# Singleton instance of the EmailService
email_service = EmailService() 