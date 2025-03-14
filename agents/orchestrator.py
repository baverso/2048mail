#!/usr/bin/env python3
"""
orchestrator.py

This script serves as the central orchestrator for the EVQLV AI Email Management System.
It integrates various agents into a single SequentialChain pipeline using LangChain.
Prompts for each agent are loaded from external text files in the 'prompts' directory.

Author: Brett Averso
Date: March 13, 2025
License: GPL-3.0
"""

import os
import logging
from langchain.llms import OpenAI
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def load_prompt(file_path):
    """
    Load a prompt from a text file.

    Args:
        file_path (str): Path to the prompt file.

    Returns:
        str: The content of the prompt file.
    """
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()

# Directory containing prompt files
PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "prompts")

# =====================
# Load Agent Prompts
# =====================
summarizer_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "email_summarizer_prompt.txt"))
needs_response_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "email_needs_response_prompt.txt"))
categorizer_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "email_categorizer_prompt.txt"))
meeting_request_decider_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "meeting_request_decider_prompt.txt"))
decline_writer_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "decline_writer_prompt.txt"))
schedule_email_writer_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "schedule_email_writer_prompt.txt"))
email_writer_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "email_writer_prompt.txt"))
editor_prompt_text = load_prompt(os.path.join(PROMPTS_DIR, "email_editor_agent_prompt.txt"))

# =====================
# Define Agent Chains
# =====================

# EMAIL_SUMMARIZER: Summarizes the incoming email into a structured summary.
summarizer_prompt = PromptTemplate(
    input_variables=["email_content", "email_chain"],
    template=summarizer_prompt_text
)
summarizer_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=summarizer_prompt,
    output_key="summary"
)

# EMAIL_NEEDS_RESPONSE: Determines if a response is needed ("respond" or "no response needed").
needs_response_prompt = PromptTemplate(
    input_variables=["summary"],
    template=needs_response_prompt_text
)
needs_response_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=needs_response_prompt,
    output_key="needs_response"
)

# EMAIL_CATEGORIZER: Categorizes the email to decide if it should be declined.
categorizer_prompt = PromptTemplate(
    input_variables=["email_content"],
    template=categorizer_prompt_text
)
categorizer_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=categorizer_prompt,
    output_key="categorizer_decision"
)

# MEETING REQUEST DECIDER: Determines if the email is solely a scheduling request.
meeting_request_decider_prompt = PromptTemplate(
    input_variables=["email_content"],
    template=meeting_request_decider_prompt_text
)
meeting_request_decider_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=meeting_request_decider_prompt,
    output_key="meeting_decision"
)

# DECLINE_WRITER: Generates a decline response.
decline_writer_prompt = PromptTemplate(
    input_variables=["email_content"],
    template=decline_writer_prompt_text
)
decline_writer_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=decline_writer_prompt,
    output_key="decline_response"
)

# SCHEDULE_EMAIL_WRITER: Generates a meeting scheduling response.
schedule_writer_prompt = PromptTemplate(
    input_variables=["email_content"],
    template=schedule_email_writer_prompt_text
)
schedule_email_writer_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=schedule_writer_prompt,
    output_key="schedule_response"
)

# EMAIL_WRITER: Generates a general response for emails.
email_writer_prompt = PromptTemplate(
    input_variables=["email_content"],
    template=email_writer_prompt_text
)
email_writer_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=email_writer_prompt,
    output_key="email_response"
)

# EMAIL_EDITOR_AGENT: Analyzes differences between AI-generated draft and user-edited email.
editor_prompt = PromptTemplate(
    input_variables=["draft_email", "edited_email"],
    template=editor_prompt_text
)
editor_chain = LLMChain(
    llm=OpenAI(temperature=0.0),
    prompt=editor_prompt,
    output_key="editor_analysis"
)

<<<<<<< HEAD
def get_user_confirmation(message, options=None):
    """
    Get user confirmation with customizable options.
    
    Args:
        message (str): The message to display to the user.
        options (dict, optional): Dictionary of valid responses mapping to return values.
                                If None, defaults to yes/no confirmation.
        
    Returns:
        str or bool: Selected option value if options provided, otherwise boolean for yes/no.
    """
    if options is None:
        options = {'y': True, 'yes': True, 'n': False, 'no': False}
    
    while True:
        option_str = f"({'/'.join(k for k in options.keys() if len(k) == 1)})"
        response = input(f"{message} {option_str}: ").strip().lower()
        if response in options:
            return options[response]
        print(f"Please enter one of: {', '.join(options.keys())}")

=======
>>>>>>> bf2e9ca4b026d495640607c8178908b1400c56c5
def orchestrate_email_response(email_input):
    """
    Orchestrates the processing of an incoming email through a series of agents
    to determine and generate an appropriate response. Optionally, if a user-edited
    version is provided, it analyzes the differences.

    Args:
        email_input (dict): A dictionary containing:
            - "email_content": Raw text of the incoming email.
            - "email_chain": (Optional) Raw text of the email chain.
            - "edited_email": (Optional) User-edited version of the AI-generated draft.

    Returns:
        str or dict: The final email response generated by the appropriate agent,
                     or if an edited email is provided, a dict with both the final response
                     and the analysis of differences.
    """
    try:
        logger.info("Starting email summarization.")
        summary_result = summarizer_chain.run(
            email_content=email_input.get("email_content", ""),
            email_chain=email_input.get("email_chain", "")
        )
        logger.info("Email summarization complete.")

        logger.info("Determining if a response is needed.")
        needs_response = needs_response_chain.run(summary=summary_result)
        needs_response = needs_response.strip().lower()
        logger.info("Needs response decision: %s", needs_response)
<<<<<<< HEAD
        
        # Confirmation point 1: Determining if email needs response
        needs_response_options = {
            'y': needs_response,
            'yes': needs_response,
            'n': 'respond' if needs_response == 'no response needed' else 'no response needed',
            'no': 'respond' if needs_response == 'no response needed' else 'no response needed'
        }
        confirmed_response = get_user_confirmation(
            f"The system determined this email {needs_response}. Is this correct?",
            needs_response_options
        )
        if confirmed_response != needs_response:
            needs_response = confirmed_response
            logger.info("User overrode needs response decision to: %s", needs_response)

        if needs_response == "no response needed":
            if get_user_confirmation("Confirm to end process with 'No response needed'?"):
                return "No response needed."
            else:
                needs_response = "respond"
                logger.info("User chose to continue process and respond")
=======

        if needs_response == "no response needed":
            return "No response needed."
>>>>>>> bf2e9ca4b026d495640607c8178908b1400c56c5

        logger.info("Categorizing the email for potential decline.")
        categorizer_decision = categorizer_chain.run(email_content=summary_result)
        categorizer_decision = categorizer_decision.strip().lower()
        logger.info("Email categorizer decision: %s", categorizer_decision)
<<<<<<< HEAD
        
        # Confirmation point 2: Categorizing the email
        categorizer_options = {
            'y': categorizer_decision,
            'yes': categorizer_decision,
            'decline': 'decline',
            'accept': 'accept'
        }
        confirmed_category = get_user_confirmation(
            f"The system categorized this as: '{categorizer_decision}'. Select 'y' to confirm, or choose 'decline'/'accept' to override:",
            categorizer_options
        )
        if confirmed_category != categorizer_decision:
            categorizer_decision = confirmed_category
            logger.info("User overrode categorizer decision to: %s", categorizer_decision)

        if categorizer_decision == "decline":
            decline_response = decline_writer_chain.run(email_content=email_input.get("email_content", ""))
            print("\nProposed Decline Response:")
            print(decline_response)
            
            # Confirmation point 3: Drafting of a decline email
            if get_user_confirmation("Do you approve this decline response?"):
                final_response = decline_response
            else:
                if get_user_confirmation("Would you like to recategorize as 'accept' instead of stopping?"):
                    categorizer_decision = "accept"
                    logger.info("User chose to recategorize as accept")
                else:
                    return "Process stopped: Decline response rejected by user."
        
        if categorizer_decision != "decline":
=======

        if categorizer_decision == "decline":
            final_response = decline_writer_chain.run(email_content=email_input.get("email_content", ""))
        else:
>>>>>>> bf2e9ca4b026d495640607c8178908b1400c56c5
            logger.info("Determining if the email is solely a scheduling request.")
            meeting_decision = meeting_request_decider_chain.run(email_content=email_input.get("email_content", ""))
            meeting_decision = meeting_decision.strip().lower()
            logger.info("Meeting request decision: %s", meeting_decision)
<<<<<<< HEAD
            
            # Confirmation point 4: Determining email type
            meeting_options = {
                'y': meeting_decision,
                'yes': meeting_decision,
                'schedule': 'schedule meeting',
                'regular': 'regular email'
            }
            confirmed_type = get_user_confirmation(
                f"The system classified this as: '{meeting_decision}'. Select 'y' to confirm, or choose 'schedule'/'regular' to override:",
                meeting_options
            )
            if confirmed_type != meeting_decision:
                meeting_decision = confirmed_type
                logger.info("User overrode meeting decision to: %s", meeting_decision)

            if meeting_decision == "schedule meeting":
                schedule_response = schedule_email_writer_chain.run(email_content=email_input.get("email_content", ""))
                print("\nProposed Schedule Response:")
                print(schedule_response)
                
                # Confirmation point 5: After drafting a scheduling email
                if get_user_confirmation("Do you approve this scheduling response?"):
                    final_response = schedule_response
                else:
                    return "Process stopped: Schedule response rejected by user."
            else:
                email_response = email_writer_chain.run(email_content=email_input.get("email_content", ""))
                print("\nProposed Email Response:")
                print(email_response)
                
                # Confirmation point 6: After drafting a response email
                if get_user_confirmation("Do you approve this email response?"):
                    final_response = email_response
                else:
                    return "Process stopped: Email response rejected by user."
=======
            if meeting_decision == "schedule meeting":
                final_response = schedule_email_writer_chain.run(email_content=email_input.get("email_content", ""))
            else:
                final_response = email_writer_chain.run(email_content=email_input.get("email_content", ""))
>>>>>>> bf2e9ca4b026d495640607c8178908b1400c56c5

        # Check if a user-edited version exists and analyze differences.
        if "edited_email" in email_input and email_input["edited_email"].strip():
            logger.info("User-edited email detected. Analyzing differences with the draft response.")
            editor_analysis = editor_chain.run(
                draft_email=final_response,
                edited_email=email_input["edited_email"]
            )
            logger.info("Email editor analysis complete.")
            return {
                "final_response": final_response,
                "editor_analysis": editor_analysis
            }
        else:
            return final_response

    except Exception as e:
        logger.error("Error in orchestrating email response: %s", str(e))
        raise

def main():
    """
    Main function to execute the email orchestration pipeline.
    """
    # Example email input for testing.
    sample_email = {
        "email_content": (
            "Subject: Collaboration Proposal for AI-Antibody Discovery\n"
            "From: Dr. Susan Lee (slee@biotechlabs.com)\n"
            "Date: Tue, 25 Feb 2025 22:01:20 +0000 (UTC)\n\n"
            "Dear Andrew,\n\n"
            "I hope you're doing well. I wanted to follow up on our discussion from last week "
            "regarding a potential collaboration between EVQLV and BiotechLabs. We're particularly "
            "interested in exploring how your AI platform can accelerate our early antibody screening "
            "processes.\n\n"
            "Would you be available for a call next Tuesday at 3 PM EST to discuss potential next steps? "
            "Let me know if that time works or if you'd prefer an alternative.\n\n"
            "Looking forward to your thoughts.\n\n"
            "Best,\nSusan"
        ),
        "email_chain": (
            "From: Brett Averso <baverso@evqlv.com>\n"
            "Sent: 20 Dec 2024 17:06\n"
            "To: Susan Lee\n"
            "Subject: Fwd: Antibody data package\n"
            "...\n"
        )
        # "edited_email": "User-edited version of the draft response..."
    }
    response = orchestrate_email_response(sample_email)
    print("Final Email Response:")
    print(response)

if __name__ == "__main__":
    main()