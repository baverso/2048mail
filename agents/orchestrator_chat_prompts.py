#!/usr/bin/env python3
"""
orchestrator.py

This script serves as the central orchestrator for the EVQLV AI Email Management System.
It integrates the retrieval and parsing modules along with various LangChain agent chains 
to process incoming emails.

Author: Brett Averso
Date: March 13, 2025
License: GPL-3.0
"""

import os
import json
import logging
from pathlib import Path
from langchain_openai import OpenAI
from langchain.chains import LLMChain
from langchain_core.prompts import PromptTemplate, ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# Import retrieval and parsing modules
from tools.email_retriever import EmailRetriever
from tools.email_parser import EmailParser
from libs.api_manager import setup_openai_api

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load API keys and set up OpenAI API
setup_openai_api()

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

# Use the newer LangChain interface with LCEL (LangChain Expression Language)
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

# Create a model with temperature=0
model = ChatOpenAI(temperature=0, model="gpt-4o-mini")
output_parser = StrOutputParser()

# EMAIL_SUMMARIZER: Summarizes the incoming email into a structured summary.
# Create a completely new prompt template without any variables from the original prompt files
summarizer_system_message = """
{{summarizer_prompt_text}}
"""

summarizer_human_message = """
Email content: {email_content}
"""

summarizer_prompt = ChatPromptTemplate.from_messages([
    ("system", summarizer_system_message),
    ("human", summarizer_human_message)
])
summarizer_chain = summarizer_prompt | model | output_parser

# NEEDS_RESPONSE: Determines if the email needs a response.
needs_response_system_message = """
{{needs_response_prompt_text}}
"""

needs_response_human_message = """
Email summary: {summary}
"""

needs_response_prompt = ChatPromptTemplate.from_messages([
    ("system", needs_response_system_message),
    ("human", needs_response_human_message)
])
needs_response_chain = needs_response_prompt | model | output_parser

# CATEGORIZER: Categorizes the email.
categorizer_system_message = """
{{categorizer_prompt_text}}
"""

categorizer_human_message = """
Email content: {email_content}
"""

categorizer_prompt = ChatPromptTemplate.from_messages([
    ("system", categorizer_system_message),
    ("human", categorizer_human_message)
])
categorizer_chain = categorizer_prompt | model | output_parser

# MEETING_REQUEST_DECIDER: Determines if the email is solely a meeting request.
meeting_request_decider_system_message = """
{{meeting_request_decider_prompt_text}}
"""

meeting_request_decider_human_message = """
Email content: {email_content}
"""

meeting_request_decider_prompt = ChatPromptTemplate.from_messages([
    ("system", meeting_request_decider_system_message),
    ("human", meeting_request_decider_human_message)
])
meeting_request_decider_chain = meeting_request_decider_prompt | model | output_parser

# DECLINE_WRITER: Writes a polite email declining the request.
decline_writer_system_message = """
{{decline_writer_prompt_text}}
"""

decline_writer_human_message = """
Email content: {email_content}
"""

decline_writer_prompt = ChatPromptTemplate.from_messages([
    ("system", decline_writer_system_message),
    ("human", decline_writer_human_message)
])
decline_writer_chain = decline_writer_prompt | model | output_parser

# SCHEDULE_WRITER: Writes a response to schedule a meeting.
schedule_writer_system_message = """
{{schedule_email_writer_prompt_text}}
"""

schedule_writer_human_message = """
Email content: {email_content}
"""

schedule_writer_prompt = ChatPromptTemplate.from_messages([
    ("system", schedule_writer_system_message),
    ("human", schedule_writer_human_message)
])
schedule_email_writer_chain = schedule_writer_prompt | model | output_parser

# EMAIL_WRITER: Writes a response to the email.
schedule_writer_prompt = ChatPromptTemplate.from_messages([
    ("system", schedule_writer_system_message),
    ("human", schedule_writer_human_message)
])
schedule_email_writer_chain = schedule_writer_prompt | model | output_parser

# EMAIL_WRITER: Writes a response to the email.
email_writer_system_message = """
{{email_writer_prompt_text}}
"""

email_writer_human_message = """
Email content: {email_content}
"""

email_writer_prompt = ChatPromptTemplate.from_messages([
    ("system", email_writer_system_message),
    ("human", email_writer_human_message)
])
email_writer_chain = email_writer_prompt | model | output_parser

# EDITOR: Analyzes the differences between the draft email and the edited version.
editor_system_message = """
{{editor_prompt_text}}
"""

editor_human_message = """
Draft email: {draft_email}
Edited email: {edited_email}
"""

editor_prompt = ChatPromptTemplate.from_messages([
    ("system", editor_system_message),
    ("human", editor_human_message)
])
editor_chain = editor_prompt | model | output_parser

def orchestrate_email_response():
    """
    Orchestrates the processing of incoming emails by retrieving raw email threads,
    parsing them into a structured format, and then passing them through LangChain agents
    to generate the appropriate email response.

    Returns:
        str or dict: The final email response or, if human-edited feedback exists,
                     a dict containing both the final response and the editor analysis.
    """
    try:
        # Retrieve raw emails using EmailRetriever.
        retriever = EmailRetriever()
        threads = retriever.retrieve_emails(n=10)

        # Parse raw emails using EmailParser.
        parser = EmailParser(retriever.service)
        structured_emails = parser.parse_emails(threads)
        
        # Filter for the most recent emails (order=1)
        # recent_emails = [email for email in structured_emails if email.get('order') == 1]
        recent_emails = [email for email in structured_emails if email.get('order') in [1, 2, 3]]

        
        # Check if we have any emails to process
        if not recent_emails:
            logger.info("No recent emails (order=1, 2, 3) found to process.")
            return "No emails to process."
        
        import pprint
        pprint.pprint(recent_emails)
        # Process the first recent email
        email_data = recent_emails[0]
        
        # Get the message_data if it exists, otherwise use the email_data directly
        if 'message_data' in email_data:
            message_data = email_data['message_data']
        else:
            message_data = email_data
        
        logger.info("Starting email summarization.")
        # Convert message_data to JSON string for the LLM
        email_content_input = json.dumps(message_data)
        summary_result = summarizer_chain.invoke({"email_content": email_content_input})
        logger.info("Email summarization complete.")

        logger.info("Determining if a response is needed.")
        needs_response = needs_response_chain.invoke({"summary": summary_result})
        needs_response = needs_response.strip().lower()
        logger.info("Needs response decision: %s", needs_response)
        
        if needs_response == "no response needed":
            return "No response needed."
        
        logger.info("Categorizing the email.")
        categorizer_decision = categorizer_chain.invoke({"email_content": email_content_input})
        categorizer_decision = categorizer_decision.strip().lower()
        logger.info("Email categorizer decision: %s", categorizer_decision)
        
        if categorizer_decision == "decline":
            final_response = decline_writer_chain.invoke({"email_content": email_content_input})
        else:
            logger.info("Determining if the email is solely a scheduling request.")
            meeting_decision = meeting_request_decider_chain.invoke({"email_content": email_content_input})
            meeting_decision = meeting_decision.strip().lower()
            logger.info("Meeting request decision: %s", meeting_decision)
            if meeting_decision == "schedule meeting":
                final_response = schedule_email_writer_chain.invoke({"email_content": email_content_input})
            else:
                final_response = email_writer_chain.invoke({"email_content": email_content_input})

        # Optionally, if human-edited feedback is provided, analyze differences.
        if "edited_email" in message_data and message_data["edited_email"].strip():
            editor_analysis = editor_chain.invoke({
                "draft_email": final_response,
                "edited_email": message_data["edited_email"]
            })
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
    Main function to run the orchestrator.
    """
    response = orchestrate_email_response()
    print("Final Email Response:")
    print(response)

if __name__ == "__main__":
    main()