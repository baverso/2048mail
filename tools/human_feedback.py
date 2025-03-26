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

def get_yes_no_feedback(prompt=None, decision=None, context=None):
    """
    Get yes/no feedback from a human user.
    
    Args:
        prompt (str, optional): The question to ask the user.
        decision (str, optional): The AI's decision that is being validated.
        context (str or object, optional): Additional context to display to the user.
        
    Returns:
        tuple: (is_correct, human_input) where:
            - is_correct (bool): True if the human agrees with the AI decision, False otherwise.
            - human_input (str): The raw input from the human ('y' or 'n').
    """
    if prompt is None:
        if decision == "respond":
                prompt = "I think we should respond."
        elif decision == "no response needed":
            prompt = "This email does not need a response."
        elif decision == "decline":
            prompt = "I think we should politely decline."
        elif decision == "move forward":
            prompt = "I think we should draft a response."
        elif decision == "schedule meeting":
            prompt = "I think we should setup a meeting."
        elif decision == "other email":
            prompt = "Placeholder for binary questions here." # TODO: Add binary questions here.
        else:
            raise ValueError(f"Invalid needs_response decision: {decision}")
    

    # Display context if provided
    if context:
        if isinstance(context, dict):
            for key, value in context.items():
                if isinstance(value, list):
                    print(f"{key}:")
                    [print('    \n',i) for i in value]
                else:
                    print(f"{key}: {value}")
        else:
            print(context)
    
    # Get human input
    while True:
        human_input = input(f"\n\nHUMAN FEEDBACK REQUESTED:\n{prompt} Wrong \U0001F44E Correct\U0001F44D (please reply with 'correct' or 'wrong')").strip().lower()
        if human_input in ['correct', 'wrong']:
            break
        print("Please enter 'correct' or 'wrong'.")
    
    # Log the feedback
    is_correct = human_input == 'correct'
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