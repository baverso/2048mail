from typing import Dict, Optional
from fastapi import Request
import logging
import uuid

from devserver.models.user_state import UserTaskState, DraftEmail

logger = logging.getLogger(__name__)

class UserStateService:
    """Service for managing user state."""
    
    def __init__(self):
        # Dictionary to store user-specific task states
        self._user_states: Dict[str, UserTaskState] = {}
        self._last_connected_user_id: Optional[str] = None
        
    def get_user_state(self, user_id: str) -> UserTaskState:
        """Get or create a user state based on user ID."""
        if user_id not in self._user_states:
            self._user_states[user_id] = UserTaskState()
            logger.info(f"Created new user state for user {user_id}")
        return self._user_states[user_id]
    
    def get_last_connected_user_id(self) -> Optional[str]:
        """Get the last connected user ID."""
        return self._last_connected_user_id
    
    def set_last_connected_user_id(self, user_id: str) -> None:
        """Set the last connected user ID."""
        self._last_connected_user_id = user_id
        logger.info(f"Updated last connected user ID to {user_id}")
    
    async def get_current_user_id(self, request: Request) -> str:
        """
        Get the current user ID from the session or create a new one.
        Returns a unique user ID for the session.
        """
        if "user_id" not in request.session or request.session["user_id"] == "none":
            # Generate a new random user ID if not authenticated
            request.session["user_id"] = str(uuid.uuid4())
            logger.info(f"Created new user ID: {request.session['user_id']}")
        
        # Always prefer the last connected user ID if available, for consistency
        if self._last_connected_user_id:
            logger.info(f"Using last connected user ID instead of session: {self._last_connected_user_id}")
            return self._last_connected_user_id
        
        return request.session["user_id"]
    
    def extract_draft_email_data(self, results) -> DraftEmail:
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
            return DraftEmail(
                email_content=draft_email,
                subject=draft_subject,
                recipient=draft_recipient
            )
        else:
            logger.info("No draft email found in any expected location in results")
            return None

# Singleton instance of the UserStateService
user_state_service = UserStateService()