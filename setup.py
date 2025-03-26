from setuptools import setup, find_packages

setup(
    name="2048mail",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "google-api-python-client>=2.108.0",  # for Gmail API
        "google-auth-oauthlib>=1.1.0",        # for OAuth flow
        "email-reply-parser>=0.5.12",         # for parsing email replies
        "pytz>=2024.1",                       # for timezone handling
        "langchain-openai>=0.0.5",            # for AI processing
        "langchain>=0.3.20",                  # for LangChain functionality
        "langchain-core>=0.3.41",             # for LangChain core components
        "python-dotenv>=1.0.0",               # for environment variables
    ],
    extras_require={
        "dev": [
            "pytest>=8.0.0",
            "black>=24.1.1",
            "flake8>=7.0.0",
            "mypy>=1.8.0",
        ],
    },
    author="Brett Averso",
    description="A Gmail-based AI email management system",
    license="GPL-3.0",
    python_requires=">=3.9",
) 