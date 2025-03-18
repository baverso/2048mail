"""
A module for archiving Gmail emails by removing the "INBOX" label
and adding the "NO RESPONSE NEEDED" label.

This module provides a function to modify an email using the Gmail API.
"""

import logging

logging = logging.getLogger(__name__)

def get_or_create_label(service, label_name):
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

def archive_email(service, message_id):
    """
    Archive an email by removing the "INBOX" label and adding the
    "NO RESPONSE NEEDED" label.
    """
    try:
        # Get or create the custom label and retrieve its ID
        custom_label_id = get_or_create_label(service, "NO RESPONSE NEEDED")
        
        # Modify the message: remove INBOX and add the custom label
        modified_message = service.users().messages().modify(
            userId='me',
            id=message_id,
            body={
                'removeLabelIds': ['INBOX'],
                'addLabelIds': [custom_label_id]
            }
        ).execute()
        
        logging.info("Email archived successfully: %s", modified_message)
        return modified_message
    except Exception as error:
        logging.error("An error occurred while archiving the email: %s", error)
        raise