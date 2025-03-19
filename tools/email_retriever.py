#!/usr/bin/env python3
"""
email_retriever.py

This module handles the retrieval of raw email data from the Gmail API.
It uses helper functions to retrieve the last n email threads from the Gmail INBOX,
and includes functionality to retrieve a specific email message from a thread.

Author: Brett Averso
Date: March 13, 2025
License: GPL-3.0
"""

import logging
from typing import List, Dict, Any
from googleapiclient.discovery import build
from libs.google_oauth import get_gmail_credentials
from tools.check_email import get_last_n_emails
import time

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

class EmailRetriever:
    """
    Retrieves raw email data from the Gmail API.
    """
    def __init__(self) -> None:
        self.service = None

    def initialize_service(self) -> None:
        """
        Initializes the Gmail API service using credentials.
        """
        try:
            creds = get_gmail_credentials()
            self.service = build('gmail', 'v1', credentials=creds)
            logger.info("Gmail service initialized.")
        except Exception as e:
            logger.error("Failed to initialize Gmail service: %s", e)
            raise

    def retrieve_emails(self, n: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves the last n email threads from the Gmail INBOX.

        Args:
            n (int): Number of threads to retrieve.

        Returns:
            List[Dict[str, Any]]: List of raw email thread dictionaries.
        """
        if self.service is None:
            self.initialize_service()
        threads = get_last_n_emails(self.service, n)
        if not threads:
            logger.error("No emails found in INBOX.")
            raise SystemExit("No emails found in INBOX.")
        return threads

    def retrieve_email_message(self, message_id: str) -> Dict[str, Any]:
        """
        Retrieves a specific email message using its message ID.

        Args:
            message_id (str): The ID of the email message to retrieve.

        Returns:
            Dict[str, Any]: The full email message retrieved from the Gmail API.
        """
        if self.service is None:
            self.initialize_service()
        try:
            message = self.service.users().messages().get(userId='me', id=message_id, format='full').execute()
            logger.info("Retrieved email message with ID: %s", message_id)
            return message
        except Exception as e:
            logger.error("Failed to retrieve email message with ID %s: %s", message_id, e)
            raise

if __name__ == "__main__":
    retriever = EmailRetriever()
    # Example: Retrieve the last 5 email threads.
    threads = retriever.retrieve_emails(n=10)
    # Example: Retrieve a specific message if available.
    if threads:
        for thread in threads:
            if thread.get("messages"):
                first_message_id = thread["messages"][0].get("messageId")
                time.sleep(1)
                if first_message_id:
                    message = retriever.retrieve_email_message(first_message_id)
                    print(message.get('threadId'))
                    print(message.get('id'))
                    print(message.get('snippet'))
                    print(message.get('labelIds'))
                    print('--------------------------------')