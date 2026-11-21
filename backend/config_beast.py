

"""
ULTIMATE BEAST CONFIGURATION
============================
Status: GODZILLA_MODE
Strict Type-Safety | Aggressive Defaults | Pydantic V2

Replaces legacy flat config with modular, domain-specific settings.
"""

from __future__ import annotations
import os
from typing import Literal, Optional, List, Dict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator, model_validator, SecretStr

# ==========================================
# 1. ORCHESTRATION CONFIG (GODZILLA LAYER)
# ==========================================
class OrchestrationConfig(BaseSettings):
    """Configuration for the Godzilla Swarm Manager."""
    
    max_parallel_agents: int = Field(
        default=10,
        ge=1,
        le=1000,
        description="Maximum concurrent agents in swarm.",
        env="MAX_PARALLEL_AGENTS"
    )    
    singularity_mode: bool = Field(
        default=True,
        description="Enable adaptive scaling based on load.",
        env="ENABLE_SINGULARITY_MODE"
    )
    
    overmind_poll_interval: int = Field(
        default=5,
        description="Seconds between Overmind drift checks.",
        env="OVERMIND_POLL_INTERVAL"
    )
    
    circuit_breaker_threshold: int = Field(
        default=5,
        description="Failures before isolating a subsystem.",
        env="CIRCUIT_BREAKER_THRESHOLD"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# ==========================================
# 2. NEO4J KNOWLEDGE GRAPH (TRUTH LAYER)
# ==========================================
class Neo4jConfig(BaseSettings):
    """Strict configuration for Neo4j Database."""
    
    uri: str = Field(
        default="bolt://localhost:7687", 
        description="Neo4j Connection URI",
        env="NEO4J_URI"
    )
    user: str = Field(
        default="neo4j", 
        env="NEO4J_USER"
    )
    password: str = Field(
        default="", 
        description="Database password. If empty, Graph is disabled.",
        env="NEO4J_PASSWORD"
    )
    database: str = Field(
        default="neo4j",
        env="NEO4J_DATABASE"
    )
    
    max_connection_pool_size: int = Field(
        default=10,
        description="Connection pool for high-concurrency swarms.",
        env="NEO4J_POOL_SIZE"
    )

    @field_validator("uri")
    @classmethod
    def validate_uri(cls, v: str) -> str:
        if not v.startswith(("bolt://", "neo4j://")):
            raise ValueError("URI must start with bolt:// or neo4j://")
        return v

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

# ==========================================
# 3. RESEARCH CONFIG (USER CHOICES)
# ==========================================
class ResearchConfig(BaseSettings):
    """
    Configuration for Deep Research & Discovery Mode.
    
    USER CHOICES (via API):
    - mode: "research" or "discovery"
    - runtime_hours: 12, 24, 48, or 72
    
    Everything else is hardcoded.
    """
    
    # The 2 USER CHOICES
    mode: Literal["research", "discovery"] = Field(
        default="research",
        description="Research mode: 'research' (focused) or 'discovery' (exploratory).",
        env="RESEARCH_MODE"
    )

    runtime_hours: float = Field(
        default=12.0,
        ge=0.1,
        le=72.0,
        description="User-selected research duration in hours.",
        env="RESEARCH_RUNTIME_HOURS"
    )
    
    # Internal defaults (NOT user configurable)
    max_iterations: int = Field(
        default=1,
        ge=1,
        description="Maximum research depth iterations (internal).",
    )
    
    enable_discovery_engine: bool = Field(
        default=True,
        description="Enable GWT-Attention-Mode for prioritized hypothesis generation.",
    )

    paper_read_target: int = Field(
        default=1,
        description="[RIGOR] FLAW 14 FIX: Realistic target for abstract scanning based on rate limits.",
        env="PAPER_READ_TARGET"
    )

    deep_read_target: int = Field(
        default=1,
        description="[RIGOR] FLAW 14 FIX: Realistic target for deep PDF parsing based on rate limits.",
        env="DEEP_READ_TARGET"
    )

    enable_skill_rag: bool = Field(
        default=True,
        description="Enable SVEL-style Skill RAG (Tutorial Mode) for experiments.",
        env="ENABLE_SKILL_RAG"
    )
    
    semantic_scholar_api_key: Optional[str] = Field(
        default=None,
        env="SEMANTIC_SCHOLAR_API_KEY"
    )

    pubmed_email: Optional[str] = Field(
        default=None,
        description="Required for high-rate PubMed access.",
        env="PUBMED_EMAIL"
    )

    # --- SCIENTIFIC RIGOR (EPISTEMIC MANIFOLD) ---
    scientific_alpha: float = Field(
        default=0.05,
        ge=0.0000001,
        le=0.2,
        description="The 'Skepticism Dial' (p-value threshold). Lower = Harder Science.",
        env="SVEL_ALPHA"
    )

    uncertainty_level: float = Field(
        default=0.95,
        ge=0.5,
        le=0.999,
        description="Confidence level for reported intervals (e.g., 0.95 = 95% CI).",
        env="SVEL_CONFIDENCE_LEVEL"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

# ==========================================
# 4. SAFETY & GOVERNANCE (OVERMIND)
# ==========================================
class SafetyConfig(BaseSettings):
    """Safety thresholds and constraints."""
    
    max_runtime_hours: float = Field(
        default=76.0,
        ge=0.1,
        le=100.0,
        description="Hard stop for autonomous loops.",
        env="MAX_RUNTIME_HOURS"
    )

    require_human_confirmation: bool = Field(        default=False,
        description="If True, blocks on critical actions.",
        env="REQUIRE_HUMAN_CONFIRMATION"
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )

# ==========================================
# MAGIX AGGREGATE CONFIG
# ==========================================
class BeastSystemConfig(BaseSettings):
    """
    ROOT CONFIGURATION OBJECT.
    Aggregates all sub-modules for single-point entry.
    """
    env: Literal["dev", "prod", "test"] = Field(default="dev", env="ENV")
    
    orchestration: OrchestrationConfig = Field(default_factory=OrchestrationConfig)
    neo4j: Neo4jConfig = Field(default_factory=Neo4jConfig)
    research: ResearchConfig = Field(default_factory=ResearchConfig)
    safety: SafetyConfig = Field(default_factory=SafetyConfig)
    
    # Generic API Keys
    # F-56: Pydantic Secret Leak Protection
    # Using SecretStr prevents these from being dumped in plaintext logs or debug endpoints.
    openai_api_key: SecretStr = Field(default="", env="OPENAI_API_KEY")
    moonshot_api_key: SecretStr = Field(default="", env="MOONSHOT_API_KEY")
    
    @field_validator("env", mode="before")
    @classmethod
    def normalize_env(cls, v: str) -> str:
        if v.lower().startswith("dev"):
            return "dev"
        if v.lower().startswith("prod"):
            return "prod"
        return v

    @property
    def is_prod(self) -> bool:
        return self.env == "prod"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Global Singleton
def _init_beast_config():
    """
    Initialize config with User Data overrides (Productization).
    Injects settings.json values into os.environ so BaseSettings picks them up recursively.
    """
    try:
        from backend.core.settings_manager import settings_manager
        user_settings = settings_manager.get_all_secrets()
        
        for k, v in user_settings.items():
            if v is not None:
                # 1. Update Env Var (Upper Case for Standard Pydantic)
                os.environ[k.upper()] = str(v)
                # 2. Update Env Var (As Is - just in case)
                os.environ[k] = str(v)
                
    except ImportError:
        pass # SettingsManager might not be ready during early bootstrap
    except Exception:
        pass

    return BeastSystemConfig()

beast_config = _init_beast_config()

