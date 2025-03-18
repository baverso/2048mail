"""
json_extractor.py

Utility functions for extracting JSON from model outputs.

Author: Brett Averso
Date: March 13, 2025
License: GPL-3.0
"""

def extract_json_from_model_output(model_result):
    """
    Extracts JSON from model output text, handling various output formats.
    
    Args:
        model_result (str): Raw text output from the model
        
    Returns:
        str: Extracted JSON string
    """
    # Check if output follows "Expected Output:" format
    if "Expected Output:" in model_result:
        json_str = model_result.split("Expected Output:", 1)[1].strip()
    else:
        # Find JSON in the output using braces
        json_start = model_result.find('{')
        json_end = model_result.rfind('}') + 1
        if json_start >= 0 and json_end > json_start:
            json_str = model_result[json_start:json_end]
        else:
            # If no JSON structure found, return the raw output
            json_str = model_result
    
    return json_str 