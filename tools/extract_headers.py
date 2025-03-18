import email.utils
from datetime import datetime
import pytz
from tools.text_cleaner import clean_text

def extract_headers(message: dict) -> dict:
    """
    Extract header fields from a Gmail message and return them in a dictionary.

    Args:
        message (dict): A dictionary representing a Gmail message, expected to contain:
                        - "payload": dict containing message payload
                        - "headers": list of header dicts with "name" and "value"
                        - "labelIds": list of Gmail label IDs

    Returns:
        dict: A dictionary containing header fields including:
              - subject: The email subject
              - from: The sender's email address
              - to: The recipient email address(es)
              - cc: Carbon copy recipients (if any)
              - bcc: Blind carbon copy recipients (if any) 
              - reply-to: Reply-to address (if any)
              - date: The date in EST timezone (YYYY-MM-DD HH:MM:SS format)
              - labelIds: List of Gmail label IDs
    """
    payload = message.get("payload", {})
    headers = payload.get("headers", [])
    
    date_str = ""
    valid_keys = {"subject",
                  "from",
                  "to",
                  "cc",
                  "bcc",
                  "reply-to"}  # valid keys
    # do NOT include labelIds or date. They require special processing.

    result = {}
    for header in headers:
        key = header.get("name", "").lower()
        if key in valid_keys:
            result[key] = clean_text(header.get("value", ""))
        elif key == "date":
            raw_date = header.get("value", "")
            dt = email.utils.parsedate_to_datetime(raw_date)
            eastern = pytz.timezone("US/Eastern")
            dt_est = dt.astimezone(eastern)
            dt_naive = dt_est.replace(tzinfo=None)  # Remove tzinfo
            date_str = dt_naive.strftime("%Y-%m-%d %H:%M:%S")
            result[key] = date_str
    
    return result # update message_data in main script with this