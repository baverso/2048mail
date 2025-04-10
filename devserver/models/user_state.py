from typing import Optional, Any, Dict
from pydantic import BaseModel, Field


class BackgroundTaskState(BaseModel):
    """State of a background task for a specific user."""
    running: bool = False
    status: str = "idle"
    results: Optional[Any] = None
    current_email: Optional[str] = None
    feedback_required: bool = False
    user_id: Optional[str] = None
    thread_name: Optional[str] = None
    draft_email: Optional[str] = None
    draft_subject: Optional[str] = None
    draft_recipient: Optional[str] = None


class UserTaskState(BaseModel):
    """Model representing a user's task state."""
    background_task: BackgroundTaskState = Field(default_factory=BackgroundTaskState)


class DraftEmail(BaseModel):
    """Model representing a draft email."""
    email_content: str
    subject: Optional[str] = None
    recipient: Optional[str] = None
    draft_id: Optional[str] = None 