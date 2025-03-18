#!/usr/bin/env python3
"""
Module for extracting MIME type from a Gmail message.
"""

def extract_message_mime_type(message: dict) -> dict:
    """
    Extract MIME type from the given Gmail message.

    Args:
        message (dict): A dictionary representing a Gmail message.

    Returns:
        dict: A dictionary containing the MIME type under the key "mimeType".
    """
    result = {}
    payload = message.get("payload", {})
    result["mimeType"] = payload.get("mimeType", "")
    return result