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