"""Environment configuration centralization.

Loads environment variables (via python-dotenv if available) and exposes them for other modules.
"""
from dotenv import load_dotenv
import os

# Load .env if present
load_dotenv()

# Core keys
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")

# Model names / defaults
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-2.1")

# Frontend/API
API_URL = os.getenv("API_URL", "http://localhost:8000")

# Small helper
def require_key(name: str, value: str):
    if not value:
        raise RuntimeError(f"{name} not configured in environment")
    return value
