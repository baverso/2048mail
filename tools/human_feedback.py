#!/usr/bin/env python3
"""
human_feedback.py

This module provides functions for collecting human feedback during the email processing workflow.
It allows for human-in-the-loop validation of AI decisions at various stages of the process.

Author: Brett Averso
Date: March 15, 2025
License: GPL-3.0
"""

import logging
import pprint
# Configure logging
logger = logging.getLogger(__name__)

def get_yes_no_feedback(prompt, decision=None, context=None):
    """
    Get yes/no feedback from a human user.
    
    Args:
        prompt (str): The question to ask the user.
        decision (str, optional): The AI's decision that is being validated.
        context (str or object, optional): Additional context to display to the user.
        
    Returns:
        tuple: (is_correct, human_input) where:
            - is_correct (bool): True if the human agrees with the AI decision, False otherwise.
            - human_input (str): The raw input from the human ('y' or 'n').
    """

    # Display context if provided
    if context:
        if isinstance(context, dict):
            for key, value in context.items():
                if isinstance(value, list):
                    print(f"{key}:\n")
                    [print('    ',i) for i in value]
                else:
                    print(f"{key}: {value}")
        else:
            print(context)
        
    
    # Display AI decision if provided
    if decision:
        print(f"AI Decision: {decision}")
    
    # Get human input
    while True:
        human_input = input(f"{prompt} (y/n): ").strip().lower()
        if human_input in ['y', 'n']:
            break
        print("Please enter 'y' for yes or 'n' for no.")
    
    # Log the feedback
    is_correct = human_input == 'y'
    if decision:
        if is_correct:
            logger.info(f"Human confirmed AI decision: {decision}")
        else:
            logger.info(f"Human overrode AI decision: {decision}")
    
    return is_correct, human_input

def get_feedback_with_options(prompt, options, context=None):
    """
    Get feedback from a human user with multiple options.
    
    Args:
        prompt (str): The question to ask the user.
        options (list): List of valid options the user can choose from.
        context (str or object, optional): Additional context to display to the user.
        
    Returns:
        str: The selected option.
    """
    # Display context if provided
    if context:
        pprint.pprint(f"\nContext: {context}")
    
    # Display options
    print("\nOptions:")
    for i, option in enumerate(options, 1):
        print(f"{i}. {option}")
    
    # Get human input
    while True:
        try:
            selection = input(f"{prompt} (1-{len(options)}): ").strip()
            selection_idx = int(selection) - 1
            if 0 <= selection_idx < len(options):
                selected_option = options[selection_idx]
                logger.info(f"Human selected option: {selected_option}")
                return selected_option
            else:
                print(f"Please enter a number between 1 and {len(options)}.")
        except ValueError:
            print("Please enter a valid number.") 