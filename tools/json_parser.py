#!/usr/bin/env python3
"""
json_parser.py

Utility functions for parsing JSON output from LLM responses.

Author: Brett Averso
Date: March 13, 2025
License: GPL-3.0
"""

import json
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def parse_json_output(output_text, default_value=None):
    """
    Parse JSON output from LLM response.
    
    Args:
        output_text (str): The text output from the LLM
        default_value: Value to return if parsing fails
        
    Returns:
        The parsed JSON object or default_value if parsing fails
    """
    try:
        # Check for the specific pattern we're seeing in the output
        if "Output:" in output_text:
            # Extract the text after "Output:"
            output_section = output_text.split("Output:", 1)[1].strip()
            # Now try to find JSON in this section
            json_start = output_section.find('{')
            json_end = output_section.rfind('}') + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = output_section[json_start:json_end]
                # Handle common formatting issues
                json_str = re.sub(r',\s*}', '}', json_str)
                json_str = re.sub(r',\s*]', ']', json_str)
                return json.loads(json_str)
        
        # If that didn't work, try the original approach
        json_start = output_text.find('{')
        json_end = output_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = output_text[json_start:json_end]
            # Handle common formatting issues
            json_str = re.sub(r',\s*}', '}', json_str)
            json_str = re.sub(r',\s*]', ']', json_str)
            return json.loads(json_str)
        
        # Check for specific keywords in the text
        if "respond" in output_text.lower():
            return {"needs_response": "respond"}
        elif "no response needed" in output_text.lower():
            return {"needs_response": "no response needed"}
        elif "yes" in output_text.lower() and "meeting" in output_text.lower():
            return {"is_meeting_request": "yes"}
        elif "no" in output_text.lower() and "meeting" in output_text.lower():
            return {"is_meeting_request": "no"}
        elif "decline" in output_text.lower():
            return {"category": "decline"}
        
        # If we get here, we couldn't parse the output
        logger.warning(f"Failed to parse JSON from: {output_text}")
        return default_value
    except json.JSONDecodeError as e:
        # If we get a JSON decode error, try to extract just the value
        if "needs_response" in output_text.lower():
            if "respond" in output_text.lower():
                return {"needs_response": "respond"}
            else:
                return {"needs_response": "no response needed"}
        
        logger.warning(f"JSON decode error: {e} in text: {output_text}")
        return default_value
    except Exception as e:
        logger.warning(f"Error parsing JSON: {e} from: {output_text}")
        return default_value 