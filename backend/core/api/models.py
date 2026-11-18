# backend/core/api/models.py
from enum import Enum

class Provider(str, Enum):
    """LLM Provider types."""
    OPENAI = "openai"
    GEMINI = "gemini"
    ANTHROPIC = "anthropic"
    MOONSHOT = "moonshot"
    PERPLEXITY = "perplexity" # Added for completeness

