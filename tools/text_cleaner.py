"""
Module for cleaning text.
"""

import re
import unicodedata
import html

def clean_text(text: str) -> str:
    """
    Clean the given text by:
      - Normalizing Unicode to NFC.
      - Unescaping HTML entities.
      - Removing invisible characters (e.g., zero-width spaces).
      - Removing control characters (excluding newline, tab, and space).
      - Removing URLs and image tags.
      - Collapsing multiple whitespace characters.
    
    Args:
        text (str): The input text.
        
    Returns:
        str: The cleaned text.
    """
    # Normalize text to NFC form.
    text = unicodedata.normalize('NFC', text)
    
    # Unescape HTML entities.
    text = html.unescape(text)
    
    # Remove invisible characters.
    text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text)
    
    # Remove control characters (except newline, tab, and space).
    text = ''.join(ch for ch in text if unicodedata.category(ch)[0] != 'C' or ch in '\n\t ')
    
    # Remove image tags of the form [https://...]
    text = re.sub(r'\[https?://[^\]]+\]', '', text)
    
    # Remove standalone URLs (starting with http:// or https://).
    text = re.sub(r'https?://\S+', '', text)
    
    # Collapse multiple whitespace characters into a single space and strip.
    lines = text.splitlines()
    cleaned_lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in lines]
    cleaned_text = "\n".join(cleaned_lines).strip()
    
    return cleaned_text

# Example usage:
if __name__ == '__main__':
    sample = """I am online... From: Andrew Satz asatzevqlv.comnotifybf2.hubspot.com Sent: 25 February 2025 8:00 To: Yu Wang yuwanghkhku.hk Subject: A reminder for our upcoming meeting Hello Yu, This is a friendly reminder that we have a meeting booked on: Feb 26, 2025 8:00 AM HKT (08:00) I look forward to meeting with you, Andrew Satz CEO [https:evqlv.comhubfsLogos20-20EVQLVEVQLV20logo20Blue2080h.png]https:evqlv.come3tCtcDM113cSvCQ04VVrPdN6ypFJLW1l5J7m7PQb-7W861hN75srKDxW9h9bGc6sJ8QhV1J0Lf8N84JPW8T5k356dYVbwW7pHpCm5BS6YbW61HvcX1V3WssW7Ydp3582f689W49GbZ5TQnHnN8q8qL7DhR-W1T0Rms1d081CW2cRvpf7NYVn3Vv1bM81vdN65N4LCmV8w6DJKVrPfW36PKds7N6zMGrh7YkHVW3H4RtJ66GD7RW3Ym8FQ8X-XyJ1F2 New York, NY Miami, FL"""
    cleaned = clean_text(sample)
    print("Cleaned text:")
    print(cleaned)