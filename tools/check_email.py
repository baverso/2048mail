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
import logging
import time
logger = logging.getLogger(__name__)

def get_last_n_emails(service, num_threads=50) -> list:
    """
    Retrieve up to num_threads from the user's INBOX, excluding any messages with the specified global labels.
    For each thread, collect up to MAX_MESSAGES_PER_THREAD messages and assign an "order" key to each message 
    indicating its position within the thread (1 for the first message, 2 for the next, etc.).
    Each message will include "messageId" (copied from "id"), "threadId", "order", and "labelIds".
    
    Global Exclusions:
      Exclude emails with any of these labels:
        CATEGORY_PERSONAL, CATEGORY_SOCIAL, CATEGORY_PROMOTIONS, CATEGORY_UPDATES, CATEGORY_FORUMS.
    
    The function uses the "q" parameter to initially filter out unwanted labels, but since the list() call 
    may still return messages that include some of the excluded labels, a post-filtering step is performed.
    
    Args:
        service: Authorized Gmail API service instance.
        num_threads (int, optional): Number of threads to retrieve. Defaults to 50.
    
    Returns:
        list: A list of dictionaries, each with:
              - thread_id: The thread's ID.
              - messages: A list of message dictionaries (each with "messageId", "threadId", "order", and "labelIds").
    """
    MAX_MESSAGES_PER_THREAD = 5
    time.sleep(1)

    # exclude labels
    exclude_labels = [
        ["CATEGORY_SOCIAL",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_UPDATES",
        "CATEGORY_FORUMS"],
        ["CATEGORY_SOCIAL",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_UPDATES",
        "CATEGORY_FORUMS",
        "UNREAD"],
        ["CATEGORY_SOCIAL",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_UPDATES",
        "CATEGORY_FORUMS",
        "IMPORTANT"],
        ["CATEGORY_SOCIAL",
        "CATEGORY_PROMOTIONS",
        "CATEGORY_UPDATES",
        "CATEGORY_FORUMS",
        "IMPORTANT",
        "READ"]
    ]
    
    # We only include emails in the INBOX.
    include_labels = [
        ["UNREAD","INBOX","IMPORTANT"], # ROUND 1: Inbox + Unread + Important
        ["INBOX","IMPORTANT"], # ROUND 2: Inbox + Read + Important
        ["UNREAD","INBOX"], # ROUND 3: Unread + Inbox + NOT Important 
        ["INBOX"] # ROUND 4: Inbox + Read
    ]

    # Create iterators for the label lists
    exclude_labels_iter = iter(exclude_labels)
    include_labels_iter = iter(include_labels)
    
    threads = {}  # key: threadId, value: list of messages in that thread
    
    # Flag to track if we have more label combinations to try
    has_more_label_combinations = True
    
    # Get the first set of labels
    try:
        current_exclude_labels = next(exclude_labels_iter)
        current_include_labels = next(include_labels_iter)
    except StopIteration:
        # Handle the case where either list is empty
        logger.error("Label lists cannot be empty")
        return []
    
    # Main loop - continue until we have enough threads or no more label combinations
    while len(threads) < num_threads and has_more_label_combinations:
        logger.info(f"Trying label combination - Include: {current_include_labels}, Exclude: {current_exclude_labels}")
        
        # Build a query string to preliminarily exclude unwanted labels
        exclusion_query = " ".join(f"-label:{lbl}" for lbl in current_exclude_labels)
        
        page_token = None
        # Start with first page (page_token is None) and continue while there are more pages
        first_page = True
        while len(threads) < num_threads and (first_page or page_token is not None):
            first_page = False  # After first iteration, we're no longer on first page
            params = {
                "userId": "me",
                "labelIds": current_include_labels,
                "q": exclusion_query,
                "maxResults": 100,  # Request up to 100 messages per page.
                "fields": "nextPageToken, messages(id, threadId)"
            }
            if page_token:
                params["pageToken"] = page_token

            results = service.users().messages().list(**params).execute()
            msgs = results.get("messages", [])
            
            logger.info(f"Found {len(msgs)} messages with current label combination")
            
            if not msgs:
                logger.info("No messages found with current label combination")
                break  # No messages found with current label combination
            
            for msg in msgs:
                if len(threads) >= num_threads:
                    break  # We have enough threads
                    
                thread_id = msg.get("threadId")
                # Retrieve full message to get detailed fields, including labelIds.
                full_msg = service.users().messages().get(userId="me", id=msg.get("id"), format="full").execute()
                label_ids = full_msg.get("labelIds", [])
                
                # Post-filter: skip message if any global exclusion label is present.
                if any(label in label_ids for label in current_exclude_labels):
                    continue
                
                # Prepare message: copy 'id' to 'messageId' and remove 'id'.
                msg["messageId"] = msg.get("id")
                if "id" in msg:
                    del msg["id"]
                msg["threadId"] = thread_id
                
                # Append message to the thread.
                if thread_id not in threads:
                    msg["order"] = 1
                    threads[thread_id] = [msg]
                else:
                    if len(threads[thread_id]) < MAX_MESSAGES_PER_THREAD:
                        msg["order"] = len(threads[thread_id]) + 1
                        threads[thread_id].append(msg)
            
            # Get the next page token
            page_token = results.get("nextPageToken")
            if not page_token:
                logger.info("No more pages to retrieve for current label combination")
                break  # No more pages for this label combination
        
        # If we still need more threads, try the next label combination
        if len(threads) < num_threads:
            try:
                current_exclude_labels = next(exclude_labels_iter)
                current_include_labels = next(include_labels_iter)
                logger.info("Moving to next label combination")
            except StopIteration:
                # We've exhausted all label combinations
                logger.info("No more label combinations to try")
                has_more_label_combinations = False
    
    # Flatten the threads dictionary into a list.
    threads_list = []
    for thread_id, msgs in threads.items():
        threads_list.append({
            "thread_id": thread_id,
            "messages": msgs
        })
    
    # Return only the first n threads if more were collected.
    return threads_list[:num_threads]