#!/usr/bin/env python3
"""
email_parser.py

This module contains the EmailParser class that converts raw email threads 
into structured dictionaries for use by the EVQLV AI Email Management System.

Author: Brett Averso
Date: March 13, 2025
License: GPL-3.0
"""

import logging
from typing import Dict, Any, List
from tools import extract_headers, extract_message_labels, extract_message_mime_type, extract_full_content, is_email_snoozed
from email_reply_parser import EmailReplyParser

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class EmailParser:
    """
    Parses raw email thread data into a structured format.
    """
    def __init__(self, service) -> None:
        self.service = service

    def parse_thread(self, thread: Dict[str, Any]) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        Parses a single email thread into structured email data.

        Args:
            thread (dict): A raw email thread from the Gmail API.

        Returns:
            tuple: (List of flattened email message dictionaries, Dictionary of full content by message ID)
        """
        email_messages = thread.get("messages", [])
        thread_id = thread.get("thread_id")
        flattened_messages = []
        full_content_store = {}
        
        for idx, msg in enumerate(email_messages, start=1):
            try:
                message_id = msg.get("messageId")
                message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
                
                # Create base message structure
                flattened_message = {
                    "threadId": thread_id,
                    "messageId": message_id,
                    "order": idx,
                    "message_data": {}
                }
                
                # Add all other data to message_data
                message_data = msg.copy()
                headers = extract_headers(message)
                message_data.update(headers)
                snoozed = is_email_snoozed(message)
                # is_promotional = headers.get(message)
                message_data.update(snoozed)
                labels = extract_message_labels(message)
                message_data.update(labels)
                mime_type = extract_message_mime_type(message)
                message_data.update(mime_type)
                cleaned_content = extract_full_content(message, max_chars=10000)
                if not cleaned_content.strip():
                    message_data["extraction_error"] = "Empty email content"
                    logger.error("Extraction Error: Empty email content for message %s", message_id)
                    continue

                # Store full content separately with identifiers
                full_content_store[message_id] = {
                    "threadId": thread_id,
                    "messageId": message_id,
                    "full_content": cleaned_content
                }

                # Parse the email content using EmailReplyParser
                parsed = EmailReplyParser().parse_reply(cleaned_content)
                message_data['reply'] = parsed
                # message_data['full_content'] = cleaned_content # Keeping this commented out as requested
                
                # Add message_data to flattened structure
                flattened_message["message_data"] = message_data
                flattened_messages.append(flattened_message)
            except Exception as e:
                logger.error("Error processing message: %s", e)
                continue
        
        return flattened_messages, full_content_store

    def parse_emails(self, threads: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Parses a list of raw email threads into a flattened list structure.

        Args:
            threads (list): List of raw email threads.

        Returns:
            tuple: (A flat list of structured email message entries, Dictionary of full content by message ID)
        """
        flattened_batch = []
        all_full_content = {}
        for thread in threads:
            parsed_messages, full_content = self.parse_thread(thread)
            if parsed_messages:
                flattened_batch.extend(parsed_messages)
            all_full_content.update(full_content)
        return flattened_batch, all_full_content

if __name__ == "__main__":
    # This test code assumes you have already set up the Gmail service.
    from libs.google_oauth import get_gmail_credentials
    from googleapiclient.discovery import build

    creds = get_gmail_credentials()
    service = build('gmail', 'v1', credentials=creds)
    parser = EmailParser(service)
    # Example usage with dummy threads list (you would get real threads from EmailRetriever)
    from tools.email_retriever import EmailRetriever
    retriever = EmailRetriever()
    threads = retriever.retrieve_emails(n=5)
    structured_data, full_content = parser.parse_emails(threads)
    # alternatively, you can use the following dummy threads list
    # dummy_threads = [{'thread_id': '19595d4124a5ed7d', 'messages': [{'threadId': '19595d4124a5ed7d', 'messageId': '19595d4124a5ed7d', 'order': 1}]}, {'thread_id': '1944832a4832b486', 'messages': [{'threadId': '1944832a4832b486', 'messageId': '195928f7b42b1d0f', 'order': 1}, {'threadId': '1944832a4832b486', 'messageId': '1959096417e30054', 'order': 2}, {'threadId': '1944832a4832b486', 'messageId': '1958c13058ab4e15', 'order': 3}]}, {'thread_id': '19592086ef9f234a', 'messages': [{'threadId': '19592086ef9f234a', 'messageId': '195928dd57108a21', 'order': 1}, {'threadId': '19592086ef9f234a', 'messageId': '19592086ef9f234a', 'order': 2}]}, {'thread_id': '195868b24ba8e680', 'messages': [{'threadId': '195868b24ba8e680', 'messageId': '195912dc4132dcf8', 'order': 1}]}, {'thread_id': '1958ff330f5cd299', 'messages': [{'threadId': '1958ff330f5cd299', 'messageId': '1958ff330f5cd299', 'order': 1}]}]  # Replace with actual threads
    # structured_data, _ = parser.parse_emails(dummy_threads)
    
    print("Structured Email Data:")
    import pprint
    # pprint.pprint(structured_data)

    print("\nFull Content Store:")
    pprint.pprint(full_content)