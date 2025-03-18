#!/usr/bin/env python3
"""
Module for extracting label IDs from a Gmail message.
"""

def extract_message_labels(message: dict) -> dict:
    """
    Extract label IDs from the given Gmail message.

    Args:
        message (dict): A dictionary representing a Gmail message.

    Returns:
        dict: A dictionary containing the label IDs under the key "labelIds".
    """
    result = {}
    result["labelIds"] = message.get("labelIds", [])
    return result