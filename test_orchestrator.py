#!/usr/bin/env python3
"""
test_orchestrator.py

A simple test script to verify the functionality of the orchestrator with the updated code.
This script mocks the email retrieval and parsing to test the LLM chain processing.
"""

import json
import logging
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mock email data
MOCK_EMAIL = {
    "threadId": "thread123",
    "messageId": "msg123",
    "order": 1,
    "message_data": {
        "from": "John Doe <john.doe@example.com>",
        "to": "recipient@example.com",
        "subject": "Meeting Request for Project Discussion",
        "date": "2025-03-15T10:30:00Z",
        "full_content": """
        Hello,
        
        I hope this email finds you well. I would like to schedule a meeting to discuss the progress of our project.
        
        Could we meet sometime next week, preferably on Tuesday or Wednesday afternoon?
        
        Looking forward to your response.
        
        Best regards,
        John Doe
        """
    }
}

# Mock the EmailRetriever and EmailParser classes
class MockEmailRetriever:
    def __init__(self):
        self.service = MagicMock()
    
    def retrieve_emails(self, n=10):
        return [{"thread_id": "thread123", "messages": [{"messageId": "msg123"}]}]

class MockEmailParser:
    def __init__(self, service):
        self.service = service
    
    def parse_emails(self, threads):
        return [MOCK_EMAIL]

# Apply patches
@patch('agents.orchestrator_text_completions.EmailRetriever', MockEmailRetriever)
@patch('agents.orchestrator_text_completions.EmailParser', MockEmailParser)
def test_orchestrator():
    # Import the orchestrator function
    from agents.orchestrator_text_completions import orchestrate_email_response
    
    # Run the orchestrator
    try:
        result = orchestrate_email_response()
        print("\n=== TEST RESULTS ===")
        print(f"Type of result: {type(result)}")
        print(f"Result: {result}")
        print("=== TEST PASSED ===")
        return True
    except Exception as e:
        print("\n=== TEST FAILED ===")
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        print("=== TEST FAILED ===")
        return False

if __name__ == "__main__":
    test_orchestrator() 