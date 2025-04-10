from typing import Optional, Any, Dict
from pydantic import BaseModel


class FeedbackRequest(BaseModel):
    """Request model for providing feedback."""
    feedback: bool = True
    
    
class WebSocketMessageBase(BaseModel):
    """Base model for WebSocket messages."""
    type: str
    

class StatusUpdate(WebSocketMessageBase):
    """Status update message sent via WebSocket."""
    type: str = "status_update"
    status: str
    results: Optional[Any] = None
    draft_email: Optional[str] = None
    draft_subject: Optional[str] = None
    draft_recipient: Optional[str] = None
    feedback_required: bool = False
    current_prompt: Optional[str] = None
    current_decision: Optional[str] = None
    current_context: Optional[str] = None


class FeedbackRequired(WebSocketMessageBase):
    """Feedback request message sent via WebSocket."""
    type: str = "feedback_required"
    prompt: str
    decision: Optional[str] = None
    context: Optional[str] = None


class FeedbackReceived(WebSocketMessageBase):
    """Feedback received confirmation message sent via WebSocket."""
    type: str = "feedback_received"
    status: str = "success"


class FeedbackTimeout(WebSocketMessageBase):
    """Feedback timeout message sent via WebSocket."""
    type: str = "feedback_timeout"
    message: str


class FeedbackMessage(WebSocketMessageBase):
    """Message from client providing feedback."""
    type: str = "provide_feedback"
    feedback: bool


class StatusResponse(BaseModel):
    """Response model for the status endpoint."""
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


class ProcessEmailsResponse(BaseModel):
    """Response model for the process-emails endpoint."""
    status: str
    message: str