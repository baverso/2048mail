"""
A module for managing Gmail email labels.

This module provides functions to apply specific labels to emails
based on their categorization and status.
"""

import logging


logger = logging.getLogger(__name__)

def get_or_create_label(service, label_name):
    """
    Gets a label ID by name, or creates it if it doesn't exist.
    
    Args:
        service: Gmail API service instance
        label_name: Name of the label to get or create
    
    Returns:
        The label ID
    """
    # List all labels for the user
    labels = service.users().labels().list(userId='me').execute().get('labels', [])
    
    # Look for an existing label with the given name
    for label in labels:
        if label.get('name') == label_name:
            return label.get('id')
    
    # If not found, create the label
    label_body = {
        'name': label_name,
        'labelListVisibility': 'labelShow',
        'messageListVisibility': 'show'
    }
    label = service.users().labels().create(userId='me', body=label_body).execute()
    return label.get('id')

def apply_label(service, message_id, add_labels=None, remove_labels=None):
    """
    Apply or remove labels from a message.
    
    Args:
        service: Gmail API service instance
        message_id: ID of the message to modify
        add_labels: List of label names to add
        remove_labels: List of label names to remove
    
    Returns:
        The modified message object
    """
    try:
        body = {}
        
        if add_labels:
            # Convert label names to label IDs
            add_label_ids = [get_or_create_label(service, label) for label in add_labels]
            body['addLabelIds'] = add_label_ids
            
        if remove_labels:
            # For system labels like INBOX, we can use them directly
            # For custom labels, we need to get their IDs
            remove_label_ids = []
            for label in remove_labels:
                if label.startswith('Q_') or label not in ['INBOX', 'IMPORTANT', 'DRAFT']:
                    label_id = get_or_create_label(service, label)
                    remove_label_ids.append(label_id)
                else:
                    remove_label_ids.append(label)
            body['removeLabelIds'] = remove_label_ids
        
        # Only proceed if we have labels to add or remove
        if body:
            modified_message = service.users().messages().modify(
                userId='me',
                id=message_id,
                body=body
            ).execute()
            
            logger.info("Labels modified successfully for message: %s", message_id)
            return modified_message
        
        return None
    except Exception as error:
        logger.error("An error occurred while modifying labels: %s", error)
        raise

def apply_q_archive_label(service, message_id):
    """
    Add the Q_Archive label when a message is removed from inbox.
    """
    return apply_label(service, message_id, add_labels=['Q_Archive'], remove_labels=['INBOX'])

def apply_q_no_response_needed_label(service, message_id):
    """
    Add the Q_No Response Needed label after response decision,
    ONLY if no response is needed.
    """
    return apply_label(service, message_id, add_labels=['Q_No Response Needed'], remove_labels=['Q_Response Needed', 'INBOX'])

def apply_q_decline_label(service, message_id):
    """
    Add the Q_Decline label after email categorization,
    ONLY if email is declined.
    """
    return apply_label(service, message_id, add_labels=['Q_Decline'], remove_labels=['INBOX'])

def apply_q_schedule_meeting_label(service, message_id):
    """
    Add the Q_Schedule Meeting label after email type is determined,
    if email needs scheduling.
    Also adds Important and Draft labels.
    """
    return apply_label(
        service, 
        message_id, 
        add_labels=['Q_Schedule Meeting', 'IMPORTANT'], 
        remove_labels=['INBOX']
    )

def apply_q_response_needed_label(service, message_id):
    """
    Add the Q_Response Needed label after email type is determined,
    if email needs response.
    Also adds Important and Draft labels.
    """
    return apply_label(
        service, 
        message_id, 
        add_labels=['Q_Response Needed', 'IMPORTANT'], 
        remove_labels=['INBOX','Q_No Response Needed']
    ) 

def apply_q_draft_label(service, message_id):
    """
    Add the Q_Draft label after email type is determined,
    if email needs drafting.
    """
    return apply_label(service, message_id, add_labels=['Q_Draft', 'IMPORTANT'], remove_labels=['INBOX'])