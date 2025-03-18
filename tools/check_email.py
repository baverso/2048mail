#!/usr/bin/env python3
"""
Module for checking Gmail inbox for snoozed emails.

This module provides functions to:
- Retrieve up to n threads from the user's INBOX, prioritizing messages that have
  the specified label IDs.
- For each thread, collect up to m messages (with an "order" field) and include
  keys: messageId, threadId, labelIds.
- Priority threads (e.g. with "IMPORTANT") are collected first, then threads from
  the general INBOX if needed.
"""

from googleapiclient.discovery import build
from libs.google_oauth import get_gmail_credentials

def get_last_n_emails(service, n=50, m=20, priorityLabels=None) -> list:
    """
    Retrieve up to n threads from the user's INBOX, prioritizing messages that have
    the specified label IDs. For each thread, collect up to m messages and assign an "order"
    key to each message indicating its order in that thread (1 for the first message, 2 for the next, etc.).
    Each message will have "messageId" (copied from "id"), "threadId", "order", and "labelIds".
    
    Args:
        service: Authorized Gmail API service instance.
        n (int, optional): Number of threads to retrieve. Defaults to 50.
        m (int, optional): Maximum number of messages per thread. Defaults to 20.
        priorityLabels (list, optional): A list of label combinations to prioritize.
            Default is [["UNREAD", "IMPORTANT"], ["UNREAD", "INBOX"], ["IMPORTANT"], ["INBOX"]].
    
    Returns:
        list: A list of dictionaries, each with keys:
              - thread_id: The thread's ID.
              - messages: A list of message dictionaries (each with "messageId", "threadId", "order", and "labelIds").
    """
    if priorityLabels is None:
        priorityLabels = [
            ["UNREAD", "IMPORTANT"],  # First priority: both unread and important
            ["UNREAD", "INBOX"],      # Second priority: unread inbox items
            ["IMPORTANT"],            # Third priority: any important items
            ["INBOX"]                 # Fourth priority: any inbox items
        ]

    threads = {}  # key: threadId, value: list of messages in that thread

    # Process each priority label combination
    for label_combo in priorityLabels:
        page_token = None
        while len(threads) < n:
            params = {
                "userId": "me",
                "labelIds": label_combo,
                "maxResults": 100,  # Request up to 100 messages per page
                "fields": "nextPageToken, messages(id, threadId, labelIds)"
            }
            if page_token:
                params["pageToken"] = page_token

            results = service.users().messages().list(**params).execute()
            msgs = results.get("messages", [])
            for msg in msgs:
                thread_id = msg.get("threadId")
                # Copy 'id' into 'messageId' and remove 'id'
                msg["messageId"] = msg.get("id")
                if "id" in msg:
                    del msg["id"]
                msg["threadId"] = thread_id
                # Append message into the corresponding thread list.
                if thread_id not in threads:
                    msg["order"] = 1
                    threads[thread_id] = [msg]
                else:
                    if len(threads[thread_id]) < m:
                        msg["order"] = len(threads[thread_id]) + 1
                        threads[thread_id].append(msg)
            page_token = results.get("nextPageToken")
            if not page_token:
                break  # No more pages for this label combination.
        if len(threads) >= n:
            break

    # Flatten the threads dictionary into a list of thread dictionaries.
    threads_list = []
    for thread_id, msgs in threads.items():
        threads_list.append({
            "thread_id": thread_id,
            "messages": msgs
        })
    # If more than n threads were collected, return only the first n threads.
    return threads_list[:n]

# Example usage:
# creds = get_gmail_credentials()
# service = build('gmail', 'v1', credentials=creds)
# threads = get_last_n_emails(service, n=50)
# for thread in threads:
#     print("Thread ID:", thread["thread_id"])
#     for message in thread["messages"]:
#         print("  Order:", message["order"], "Message ID:", message["messageId"], "Label IDs:", message.get("labelIds", []))