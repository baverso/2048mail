import base64
import re
from tools.text_cleaner import clean_text


def extract_full_content(message, max_chars=1000):
    """
    Recursively extracts the full plain text content from a Gmail message.
    
    This function handles:
      - Simple plain text messages.
      - HTML messages (by stripping HTML tags).
      - Multipart messages by recursively searching for the first part 
        with "text/plain" or, if not found, "text/html" content.
    
    If the extracted content exceeds max_chars, it is truncated with an appended "... [truncated]".
    
    Args:
        message (dict): A dictionary representing the full Gmail message.
        max_chars (int, optional): The maximum number of characters to return. Defaults to 10000.
    
    Returns:
        str: The plain text content of the email, possibly truncated.
    """
    payload = message.get("payload", {})

    def decode_data(data):
        try:
            return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
        except Exception as e:
            print("Error decoding data:", e)
            return ""

    def recursive_extract(payload):
        """
        Recursively search for text content in a payload.
        Returns a tuple (text, mime_type) where mime_type is the type of the found text.
        """
        mime_type = payload.get("mimeType", "")
        # Check if this payload has direct body data.
        data = payload.get("body", {}).get("data", "")
        if data:
            text = clean_text(decode_data(data))
            return text, mime_type

        # Otherwise, if there are parts, search each one recursively.
        for part in payload.get("parts", []):
            text, part_mime = recursive_extract(part)
            if text:
                # Prioritize plain text over HTML.
                if part_mime == "text/plain":
                    return text, part_mime
                # Otherwise, keep HTML as a fallback.
                elif part_mime == "text/html":
                    fallback = text, part_mime
                    # Continue searching in case a plain text part is available.
                    # If none is found, return the HTML fallback.
                    continue
        # If no text was found, return empty strings.
        return "", ""

    extracted_text, found_mime = recursive_extract(payload)
    
    # If the found content is HTML, strip HTML tags.
    if found_mime == "text/html" and extracted_text:
        extracted_text = re.sub(r'<[^>]+>', '', extracted_text)

    if len(extracted_text) > max_chars:
        extracted_text = extracted_text[:max_chars] + " ... [truncated]"

    # print(f"DEBUG: Extracted full content is:\n{extracted_text}")
    return extracted_text

def extract_structured_content(message, max_chars=1000):
    """
    Recursively extracts and structures email content from a Gmail message.
    
    This function handles:
      - Plain text and HTML messages (with HTML tags stripped).
      - Multipart messages by recursively searching for a "text/plain"
        or "text/html" part.
      - Extraction of metadata (From, To, CC, Subject, Date) from message headers.
      - Isolation of the reply portion using EmailReplyParser.
    
    If the extracted full text exceeds max_chars, it is truncated with an appended 
    "... [truncated]".
    
    Returns a dictionary with:
      - metadata: dict with sender, recipients, subject, and date.
      - full_body: the full cleaned email text (possibly truncated).
      - reply: the isolated reply portion (excluding quoted text/signatures).
      - truncated: Boolean flag indicating if truncation occurred.
    """
    payload = message.get("payload", {})

    def decode_data(data):
        try:
            return base64.urlsafe_b64decode(data.encode("ASCII")).decode("utf-8", errors="replace")
        except Exception as e:
            print("Error decoding data:", e)
            return ""

    def recursive_extract(payload):
        """
        Recursively searches for text content in the payload.
        Returns a tuple (text, mime_type) where mime_type is the content type.
        """
        mime_type = payload.get("mimeType", "")
        data = payload.get("body", {}).get("data", "")
        if data:
            text = clean_text(decode_data(data))
            return text, mime_type
        
        for part in payload.get("parts", []):
            text, part_mime = recursive_extract(part)
            if text:
                # Prioritize plain text over HTML.
                if part_mime == "text/plain":
                    return text, part_mime
                elif part_mime == "text/html":
                    fallback = text, part_mime
                    # Continue searching for a plain text version.
                    continue
        return "", ""

    extracted_text, found_mime = recursive_extract(payload)
    
    # If the content is HTML, strip HTML tags.
    if found_mime == "text/html" and extracted_text:
        extracted_text = re.sub(r'<[^>]+>', '', extracted_text)
    
    truncated = False
    if len(extracted_text) > max_chars:
        extracted_text = extracted_text[:max_chars] + " ... [truncated]"
        truncated = True

    # Extract metadata from the Gmail message headers.
    header_list = payload.get("headers", [])
    headers = {}
    for header in header_list:
        name = header.get("name", "").lower()
        value = header.get("value", "")
        headers[name] = value

    metadata = {
        "from": headers.get("from", ""),
        "to": headers.get("to", ""),
        "cc": headers.get("cc", ""),
        "subject": headers.get("subject", ""),
        "date": headers.get("date", "")
    }
    
    # Use EmailReplyParser to extract the reply portion (i.e. the latest reply).
    try:
        reply_text = EmailReplyParser.parse_reply(extracted_text)
    except Exception as e:
        print("Error parsing reply:", e)
        reply_text = extracted_text  # Fallback to full content if parsing fails

    structured_data = {
        "metadata": metadata,
        "full_body": extracted_text,
        "reply": reply_text,
        "truncated": truncated
    }
    
    return structured_data