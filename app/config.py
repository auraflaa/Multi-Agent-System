"""Configuration settings for the application."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file (optional, for local development convenience)
# Environment variables set in the shell take precedence over .env file
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent.parent

# Database path
DB_PATH = BASE_DIR / "app" / "db" / "retail.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Memory directory for session context
MEMORY_DIR = BASE_DIR / "app" / "memory" / "sessions"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# LLM Configuration
# Default to a stable Gemini model; can be overridden via LLM_MODEL env var
LLM_MODEL = os.getenv("LLM_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "google")  # google, openai, etc.


def validate_config():
    """Validate configuration on startup. Fail fast if API key is missing."""
    if not GEMINI_API_KEY:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. "
            "Set it as an environment variable: export GEMINI_API_KEY=your_key_here\n"
            "Or create a .env file (for local development only): GEMINI_API_KEY=your_key_here"
        )

# Tool catalog - defines available tools
AVAILABLE_TOOLS = {
    "get_session_context",
    "save_session_context",
    "get_user_profile",
    "update_user_name",
    "check_inventory",
    "recommend_products",
    "apply_offers",
    "calculate_payment",
    "get_fulfillment_options",
    "log_execution_trace"
}

