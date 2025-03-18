#!/usr/bin/env python3
"""
Module for checking if a Gmail email message has the "SNOOZED" label.

This module provides a function to determine if a given email message is snoozed.
"""

def is_email_snoozed(message: dict) -> bool:
    """
    Determine if the provided email message has the "SNOOZED" label.

    Args:
        message (dict): A dictionary representing a Gmail message.
                        It should include metadata with a 'labelIds' key.

    Returns:
        bool: True if the message has the "SNOOZED" label, otherwise False.
    """
    result={}
    label_ids = message.get("labelIds", [])
    result["is_snoozed"] = "SNOOZED" in label_ids
    return result