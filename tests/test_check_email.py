#!/usr/bin/env python3
"""
test_check_email.py

This module provides tests for the get_last_n_emails function in tools/check_email.py,
specifically focusing on verifying that the function correctly cycles through all 
label combinations when needed.
"""

import unittest
import json
import logging
from typing import List, Dict, Any, Tuple, Set
from collections import defaultdict

# Import the function to test
from tools.check_email import get_last_n_emails

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockGmailMessage:
    """
    Mocks a Gmail message with its full details.
    """
    def __init__(self, msg_id: str, thread_id: str, label_ids: List[str]):
        self.msg_id = msg_id
        self.thread_id = thread_id
        self.label_ids = label_ids
        self.data = {
            "id": msg_id,
            "threadId": thread_id,
            "labelIds": label_ids
        }
    
    def as_dict(self) -> Dict[str, Any]:
        return {
            "id": self.msg_id,
            "threadId": self.thread_id
        }

class MockMessagesResource:
    """
    Mocks the Gmail API messages resource.
    """
    def __init__(self, all_messages: Dict[str, MockGmailMessage]):
        self.all_messages = all_messages
        self.list_call_count = 0
        self.get_call_count = 0
        # Track which label combinations were requested
        self.requested_label_combinations = []
        
    def list(self, **kwargs):
        """Mock the messages.list method."""
        return MockListRequest(self, kwargs)
    
    def get(self, **kwargs):
        """Mock the messages.get method."""
        self.get_call_count += 1
        msg_id = kwargs.get("id")
        if msg_id in self.all_messages:
            return MockGetRequest(self.all_messages[msg_id])
        return MockGetRequest(None)

class MockListRequest:
    """
    Mocks a Gmail API list request.
    """
    def __init__(self, messages_resource: MockMessagesResource, params: Dict[str, Any]):
        self.messages_resource = messages_resource
        self.params = params
        # Track label combination for this request
        label_ids = sorted(params.get("labelIds", []))
        self.messages_resource.requested_label_combinations.append(tuple(label_ids))
    
    def execute(self) -> Dict[str, Any]:
        """Execute the mock list request and return matching messages."""
        self.messages_resource.list_call_count += 1
        
        # Get the parameters for filtering
        label_ids = set(self.params.get("labelIds", []))
        exclusion_query = self.params.get("q", "")
        exclude_labels = set()
        
        # Parse exclusion query to get excluded labels
        if exclusion_query:
            for part in exclusion_query.split():
                if part.startswith("-label:"):
                    exclude_labels.add(part[7:])  # Remove "-label:" prefix
        
        # Filter messages based on include/exclude labels
        filtered_messages = []
        for msg in self.messages_resource.all_messages.values():
            msg_labels = set(msg.label_ids)
            
            # Check if message has all required labels
            has_all_required = all(label in msg_labels for label in label_ids)
            
            # Check if message has any excluded labels
            has_excluded = any(label in msg_labels for label in exclude_labels)
            
            if has_all_required and not has_excluded:
                filtered_messages.append(msg.as_dict())
        
        # For testing purposes, limiting to 20 messages per page
        max_results = min(self.params.get("maxResults", 20), 20)
        page_messages = filtered_messages[:max_results]
        
        # If there are more messages, provide a next page token
        next_page_token = "next_token" if len(filtered_messages) > max_results else None
        
        return {
            "messages": page_messages,
            "nextPageToken": next_page_token
        }

class MockGetRequest:
    """
    Mocks a Gmail API get request.
    """
    def __init__(self, message: MockGmailMessage):
        self.message = message
    
    def execute(self) -> Dict[str, Any]:
        """Execute the mock get request and return the message data."""
        if not self.message:
            return {}
        return self.message.data

class MockUsersResource:
    """
    Mocks the Gmail API users resource.
    """
    def __init__(self, messages_resource: MockMessagesResource):
        self.messages_resource = messages_resource
    
    def messages(self):
        """Return the messages resource."""
        return self.messages_resource

class MockGmailService:
    """
    Mocks the Gmail API service.
    """
    def __init__(self, all_messages: Dict[str, MockGmailMessage]):
        self.messages_resource = MockMessagesResource(all_messages)
    
    def users(self):
        """Return the users resource."""
        return MockUsersResource(self.messages_resource)

def create_test_messages(count_per_combination: Dict[Tuple[str, ...], int]) -> Dict[str, MockGmailMessage]:
    """
    Create test messages for each label combination.
    
    Args:
        count_per_combination: Dictionary mapping label combinations to the number of messages to create
    
    Returns:
        Dictionary of MockGmailMessage objects keyed by message ID
    """
    messages = {}
    msg_id_counter = 1
    thread_id_counter = 1
    
    for labels, count in count_per_combination.items():
        for i in range(count):
            msg_id = f"msg{msg_id_counter}"
            thread_id = f"thread{thread_id_counter}"
            
            # Create a message with the specified labels
            message = MockGmailMessage(msg_id, thread_id, list(labels))
            messages[msg_id] = message
            
            msg_id_counter += 1
            thread_id_counter += 1
    
    return messages

class TestGetLastNEmails(unittest.TestCase):
    """
    Test cases for the get_last_n_emails function, focusing on label cycling.
    """
    
    def setUp(self):
        """Set up test cases."""
        # Define label combinations for testing
        self.label_combinations = [
            ("INBOX", "UNREAD", "IMPORTANT"),  # Combination 1
            ("INBOX", "IMPORTANT"),            # Combination 2
            ("INBOX", "UNREAD"),               # Combination 3
            ("INBOX",)                         # Combination 4
        ]
    
    def test_first_combination_sufficient(self):
        """Test when the first label combination has enough threads."""
        # Create 60 messages for the first combination only
        message_counts = {
            self.label_combinations[0]: 60,  # More than enough for the first combo
            self.label_combinations[1]: 0,
            self.label_combinations[2]: 0,
            self.label_combinations[3]: 0
        }
        
        # Create test messages and service
        messages = create_test_messages(message_counts)
        service = MockGmailService(messages)
        
        # Call the function to test
        threads = get_last_n_emails(service, num_threads=50)
        
        # Verify results
        self.assertEqual(len(threads), 50, "Should return exactly 50 threads")
        
        # Verify that only the first label combination was requested
        requested_combos = service.messages_resource.requested_label_combinations
        self.assertIn(self.label_combinations[0], requested_combos, 
                     "First label combination should be requested")
        
        # Check if other combinations were requested (they shouldn't be)
        self.assertNotIn(self.label_combinations[1], requested_combos, 
                        "Second combination shouldn't be requested")
        self.assertNotIn(self.label_combinations[2], requested_combos, 
                        "Third combination shouldn't be requested")
        self.assertNotIn(self.label_combinations[3], requested_combos, 
                        "Fourth combination shouldn't be requested")
    
    def test_cycle_through_all_combinations(self):
        """Test cycling through all combinations to get enough threads."""
        # Create messages distributed across all combinations
        message_counts = {
            self.label_combinations[0]: 15,  # Not enough in the first combo
            self.label_combinations[1]: 15,  # Need to go to the second combo
            self.label_combinations[2]: 15,  # Need to go to the third combo
            self.label_combinations[3]: 15   # Need to go to the fourth combo
        }
        
        # Create test messages and service
        messages = create_test_messages(message_counts)
        service = MockGmailService(messages)
        
        # Call the function to test
        threads = get_last_n_emails(service, num_threads=50)
        
        # Verify results
        self.assertEqual(len(threads), 50, "Should return exactly 50 threads")
        
        # Verify that all label combinations were requested
        requested_combos = service.messages_resource.requested_label_combinations
        for combo in self.label_combinations:
            self.assertIn(combo, requested_combos, 
                         f"Label combination {combo} should be requested")
    
    def test_partial_cycling(self):
        """Test cycling through some but not all combinations."""
        # Create messages for only the first two combinations
        message_counts = {
            self.label_combinations[0]: 25,  # Not enough in the first combo
            self.label_combinations[1]: 25,  # Enough when combined with first
            self.label_combinations[2]: 0,   # Should not need to use
            self.label_combinations[3]: 0    # Should not need to use
        }
        
        # Create test messages and service
        messages = create_test_messages(message_counts)
        service = MockGmailService(messages)
        
        # Call the function to test
        threads = get_last_n_emails(service, num_threads=50)
        
        # Verify results
        self.assertEqual(len(threads), 50, "Should return exactly 50 threads")
        
        # Verify that only the first two label combinations were requested
        requested_combos = service.messages_resource.requested_label_combinations
        self.assertIn(self.label_combinations[0], requested_combos, 
                     "First label combination should be requested")
        self.assertIn(self.label_combinations[1], requested_combos, 
                     "Second label combination should be requested")
        
        # Check if other combinations were requested (they shouldn't be if we got enough threads)
        # Note: this might fail if the implementation doesn't check thread count before moving to next combo
        self.assertNotIn(self.label_combinations[2], requested_combos, 
                        "Third combination shouldn't be requested")
        self.assertNotIn(self.label_combinations[3], requested_combos, 
                        "Fourth combination shouldn't be requested")
    
    def test_not_enough_threads(self):
        """Test when there aren't enough threads across all combinations."""
        # Create fewer messages than requested across all combinations
        message_counts = {
            self.label_combinations[0]: 10,
            self.label_combinations[1]: 10,
            self.label_combinations[2]: 10,
            self.label_combinations[3]: 10
        }
        
        # Create test messages and service
        messages = create_test_messages(message_counts)
        service = MockGmailService(messages)
        
        # Call the function to test
        threads = get_last_n_emails(service, num_threads=50)
        
        # Verify results
        self.assertEqual(len(threads), 40, "Should return all 40 available threads")
        
        # Verify that all label combinations were requested
        requested_combos = service.messages_resource.requested_label_combinations
        for combo in self.label_combinations:
            self.assertIn(combo, requested_combos, 
                         f"Label combination {combo} should be requested")
    
    def test_excluded_labels_filtering(self):
        """Test that messages with excluded labels are filtered out."""
        # Create messages with mixed labels including some that should be excluded
        excluded_combo = ("CATEGORY_SOCIAL", "INBOX", "UNREAD", "IMPORTANT")
        
        message_counts = {
            self.label_combinations[0]: 30,  # Normal messages
            excluded_combo: 20  # These should be filtered out
        }
        
        # Create test messages and service
        messages = create_test_messages(message_counts)
        service = MockGmailService(messages)
        
        # Call the function to test
        threads = get_last_n_emails(service, num_threads=50)
        
        # Verify results - should only get the 30 non-excluded messages
        self.assertEqual(len(threads), 30, "Should only include messages without excluded labels")

def main():
    """Run the tests and display results."""
    unittest.main()

if __name__ == "__main__":
    main()