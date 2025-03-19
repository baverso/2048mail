"""
A module for modifying Gmail email labels, with a default function to archive by removing the "INBOX" label.
"""

import logging

logging = logging.getLogger(__name__)

def remove_email_label(service, message_id, label_ids=None):
    """
    Remove specified labels from an email. By default, removes the "INBOX" label (archives the email).
    
    Args:
        service: The Gmail API service instance
        message_id: The ID of the message to modify
        label_ids: List of label IDs to remove. Defaults to ["INBOX"] for archiving
    
    Returns:
        The modified message object
    """
    if label_ids is None:
        label_ids = ['INBOX']
        
    try:
        # Modify the message by removing specified labels
        modified_message = service.users().messages().modify(
            userId='me',
            id=message_id,
            body={
                'removeLabelIds': label_ids,
            }
        ).execute()
        
        logging.info("Labels %s removed successfully from email: %s", label_ids, message_id)
        return modified_message
    except Exception as error:
        logging.error("An error occurred while removing labels from the email: %s", error)
        raise 