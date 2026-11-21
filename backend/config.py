# backend/config.py
"""
Centralized Configuration Management for SVEL Beast.
Type-safe settings with environment variable validation.
"""

from __future__ import annotations

import os
from typing import Optional, List
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """
    Application settings with environment variable loading.
    All settings can be driven via environment variables.
    """
    
    # ==========================================
    # API Keys
    # ==========================================
    openai_api_key: str = Field(default="", env="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", env="ANTHROPIC_API_KEY")
    moonshot_api_key: str = Field(default="", env="MOONSHOT_API_KEY")
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    nvidia_api_key: str = Field(default="", env="NVIDIA_API_KEY")
    nvidia_api_keys: str = Field(default="", env="NVIDIA_API_KEYS")
    openrouter_api_key: str = Field(default="", env="OPENROUTER_API_KEY")
    openrouter_api_keys: str = Field(default="", env="OPENROUTER_API_KEYS")
    serpapi_api_key: str = Field(default="", env="SERPAPI_API_KEY")
    
    # ==========================================
    # Database & Persistence
    # ==========================================
    database_url: str = Field(
        default="sqlite:///./data/svel.db",
        env="DATABASE_URL"
    )
    
    # ==========================================
    # Auth Security
    # ==========================================
    auth_enabled: bool = Field(default=False, env="AUTH_ENABLED")
    jwt_secret: str = Field(default="", env="JWT_SECRET")
    
    # ==========================================
    # LLM Configuration
    # ==========================================
    default_llm_model: str = Field(default="auto", env="DEFAULT_LLM_MODEL")
    kimi_model: str = Field(default="auto")  # Standardized to auto-resolution
    budget_threshold: float = Field(default=0.8, env="BUDGET_THRESHOLD")
    max_tokens: int = Field(default=32000, env="MAX_TOKENS")
    beast_max_tokens: int = Field(default=128000, env="BEAST_MAX_TOKENS")
    
    # ==========================================
    # Logging & Observability
    # ==========================================
    log_level: str = Field(default="INFO", env="BEAST_LOG_LEVEL")
    sentry_dsn: str = Field(default="", env="SENTRY_DSN")
    debug: bool = Field(default=False, env="DEBUG")
    
    # ==========================================
    # Rate Limiting (Mission-Local)
    # ==========================================
    rate_limit_default: int = Field(default=60, env="RATE_LIMIT_DEFAULT")
    rate_limit_llm: int = Field(default=30, env="RATE_LIMIT_LLM")
    rate_limit_agent: int = Field(default=20, env="RATE_LIMIT_AGENT")
    
    # ==========================================
    # Feature Flags
    # ==========================================
    enable_deep_research: bool = Field(default=True, env="ENABLE_DEEP_RESEARCH")
    
    # ==========================================
    # YAML Configuration Integration
    # ==========================================
    yaml_config: dict = Field(default_factory=dict)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"  # Prevent crashes on unknown env vars

    @property
    def models(self) -> dict:
        return self.yaml_config.get("models", {})

    @property
    def context_limits(self) -> dict:
        return self.yaml_config.get("context_limits", {})

    @property
    def orchestration(self) -> dict:
        return self.yaml_config.get("orchestration", {})

    @property
    def science(self) -> dict:
        return self.yaml_config.get("science", {})

    @property
    def execution(self) -> dict:
        return self.yaml_config.get("execution", {})

    def get_limit(self, key: str, default: int = 100000) -> int:
        """Helper to get a context or buffer limit from settings.yaml."""
        return self.context_limits.get(key, default)
    
    @field_validator("auth_enabled", mode="before", check_fields=False)
    @classmethod
    def parse_bool(cls, v):
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() not in ("false", "0", "no", "off")
        return bool(v)
    
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.auth_enabled and bool(self.jwt_secret)
    
    def validate_required_keys(self) -> List[str]:
        """Return list of missing required API keys."""
        missing = []
        if not any([
            self.openai_api_key, self.gemini_api_key, self.anthropic_api_key,
            self.nvidia_api_key, self.nvidia_api_keys, self.openrouter_api_key,
            self.openrouter_api_keys, self.moonshot_api_key
        ]):
            missing.append("At least one frontier LLM key (OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY, NVIDIA_API_KEYS, or OPENROUTER_API_KEYS)")
        if self.auth_enabled and not self.jwt_secret:
            missing.append("JWT_SECRET (required when AUTH_ENABLED=true)")
        return missing

def _load_root_settings_yaml() -> dict:
    import yaml
    from pathlib import Path
    for p in [Path("settings.yaml"), Path("../settings.yaml"), Path(__file__).resolve().parent.parent / "settings.yaml"]:
        if p.exists():
            try:
                with open(p, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            except Exception:
                pass
    return {}

@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.
    Loads environment variables and merges settings.yaml configuration.
    """
    s = Settings()
    s.yaml_config = _load_root_settings_yaml()
    return s

def reload_settings() -> Settings:
    """Force reload of settings and settings.yaml."""
    get_settings.cache_clear()
    global settings, OPENAI_API_KEY, ANTHROPIC_API_KEY, MOONSHOT_API_KEY, GEMINI_API_KEY
    settings = get_settings()
    OPENAI_API_KEY = settings.openai_api_key
    ANTHROPIC_API_KEY = settings.anthropic_api_key
    MOONSHOT_API_KEY = settings.moonshot_api_key
    GEMINI_API_KEY = settings.gemini_api_key
    return settings

# Convenience function for quick access
settings = get_settings()

# Explicit exports for research agents
OPENAI_API_KEY = settings.openai_api_key
ANTHROPIC_API_KEY = settings.anthropic_api_key
MOONSHOT_API_KEY = settings.moonshot_api_key
GEMINI_API_KEY = settings.gemini_api_key
