from setuptools import setup, find_packages

setup(
    name="2048mail",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-api-python-client",  # for Gmail API
        "google-auth-oauthlib",      # for OAuth flow
        "email-reply-parser>=0.5.12", # for parsing email replies
        "pytz",                      # for timezone handling
        "langchain-openai",          # for AI processing
        "langchain>=0.3.20",         # for LangChain functionality
        "langchain-core>=0.3.41",    # for LangChain core components
        "python-dotenv",             # for environment variables
    ],
    author="Brett Averso",
    description="A Gmail-based AI email management system",
    license="GPL-3.0",
    python_requires=">=3.9",
) 