# Quillo

Quillo is an automated email responder agent that leverages OpenAI's API, the Gmail API, and LangChain to analyze, categorize, and generate responses for incoming emails. The agent orchestrates a sequential pipeline using LangChain's **SequentialChain**, integrating multiple tasks such as summarizing emails, determining if a response is needed, categorizing emails, and drafting responses. It also employs memory modules to maintain historical email context and a vector database (e.g., Pinecone) for contextual retrieval via semantic search.

## Project Structure

```
root/
├── README.md           # Project documentation and setup instructions
├── agents              # Scripts for agents (sequential chain implementations, etc.)
├── config              # Credentials for the Gmail API and OpenAI API
├── databases           # Vector database and knowledgebase integrations
├── libs                # Utility libraries (OAuth tools, logger configuration, API wrappers)
├── logs                # Log files
├── prompts             # Prompt templates for the email tasks
├── requirements.txt    # Python dependencies
└── tools               # Utility scripts or tools not directly part of the agent chain
```

## Installation

There are two ways to install Quillo:

### 1. Using pip (Recommended)

```bash
pip install -e .
```

This will install the package in development mode with all required dependencies.

### 2. Manual Installation

1. **Clone the Repository:**
    ```bash
    git clone <repository-url>
    cd Quillo
    ```

2. **Set Up the Environment:**
    - Ensure you are using Python 3.9 or higher
    - Create and activate a virtual environment:
      ```bash
      python3 -m venv env
      source env/bin/activate  # On Windows, use: env\Scripts\activate
      ```
    - Install the dependencies:
      ```bash
      pip install -r requirements.txt
      ```

## Configuration

1. **Gmail API Setup:**
    - Place your Gmail API credentials in `config/credentials.json`
    - Run the initial setup to authenticate:
      ```bash
      python -m libs.google_oauth
      ```

2. **Environment Variables:**
    - Copy the example environment file:
      ```bash
      cp .env.example .env
      ```
    - Update `.env` with your API keys and settings

## Development Setup

For development work, install additional dependencies:

```bash
pip install -r requirements.txt[dev]
```

This includes:
- pytest for testing
- black for code formatting
- flake8 for linting
- mypy for type checking

## Pipeline Overview

MailMaestroAI uses LangChain's **SequentialChain** to construct a unified pipeline that processes incoming emails through a series of steps:

1. **Email Summarizer:** Summarizes the email content and extracts key points.
2. **Email Analyzer:** Determines whether the email requires a response.
3. **Email Categorizer:** Classifies the email into appropriate categories if a response is needed.
4. **Email Writer:** Drafts the email response.

Each task is handled by a dedicated agent that performs an OpenAI API text completion. The outputs are structured to allow seamless data flow between steps.

## Memory Modules

The pipeline integrates memory modules to preserve context from previous email threads and historical interactions. This retained context is leveraged during the email drafting process, ensuring that past conversations inform current responses for improved relevance and coherence.

## Vector Database for Contextual Retrieval

MailMaestroAI utilizes a vector database (such as Pinecone) to store embeddings of email content. This semantic search capability enables the system to retrieve relevant past emails or interactions based on the underlying meaning of the text, rather than relying solely on keyword matching.

## Running the Email Responder Agent

To execute the agent from the project's base directory, run:

```bash
python -m agents.email_responder_agent
```

This command will process incoming emails, enrich them with context, and orchestrate the sequential pipeline to generate responses.

Additional Tools and Modules
    •   Agent Tools:
The tools/ directory contains various modules for tasks such as archiving emails, sending responses, categorizing emails, and more.
    •   Prompt Templates:
All prompt templates are stored in the prompts/ directory. These templates are dynamically loaded by the agents during processing.

# License

This project is licensed under the GPL-3.0 License.

# Contact

For further inquiries or contributions, please contact the project maintainers.
