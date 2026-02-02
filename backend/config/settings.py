"""Application configuration settings."""

from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict

# Get the backend directory (where this file is located)
# __file__ is: backend/config/settings.py
# .parent is: backend/config
# .parent.parent is: backend
BACKEND_DIR = Path(
    __file__
).parent.parent.resolve()  # Use resolve() to get absolute path
# Project root (parent of backend); avoid os.getcwd() to prevent BlockingError under LangGraph ASGI
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # LLM Configuration
    # OpenRouter (default) - Unified API for 300+ models from multiple providers
    openrouter_api_key: str | None = (
        None  # Default provider (get from https://openrouter.ai/keys)
    )
    openrouter_model: str = "openai/gpt-4o-mini"  # Default model (can be: openai/gpt-4o, anthropic/claude-3.5-sonnet, etc.)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"  # OpenRouter API endpoint

    # Ollama (local, no API key needed)
    ollama_base_url: str = "http://localhost:11434"  # Local Ollama server
    ollama_api_key: str | None = None  # Optional API key for remote Ollama
    ollama_model: str = (
        "llama3.2"  # Default Ollama model (can be: llama3.2, qwen2.5, mistral, etc.)
    )

    # Alternative providers
    openai_api_key: str | None = None  # Direct OpenAI (for gpt-oss-20b)
    groq_api_key: str | None = None  # Groq provider
    anthropic_api_key: str | None = None  # Anthropic provider
    google_api_key: str | None = None  # Google provider

    default_model: str = (
        "openrouter:openai/gpt-4o-mini"  # Default model (OpenRouter, unified API)
    )

    # Token Limits (configurable to prevent rate limit errors)
    # Note: DeepAgents adds significant overhead (~9000 tokens for system prompt + middleware)
    # For Groq free tier (6000 TPM), this means very little room for user messages
    # Recommendation: Set to 5500 for free tier, or upgrade to Dev Tier for higher limits
    # Available for user message ≈ max_tokens_per_request - 9000
    # For Ollama (local) and OpenRouter (high limits), token limits are automatically disabled
    # For providers with strict limits (Groq free tier), set ENABLE_TOKEN_LIMITS=true and appropriate MAX_TOKENS_PER_REQUEST
    enable_token_limits: bool = True  # Set to False to disable token limits globally
    max_tokens_per_request: int = 100000  # Maximum tokens per request (default: 100K, set lower for strict providers like Groq free tier)

    # Real Estate APIs
    rapidapi_key: str | None = None

    # Location Services (optional)
    heigit_api_key: str | None = None  # For OpenRouteService (optional)

    # Bright Data (Phase 3)
    bright_data_api_token: str | None = None
    web_unlocker_zone: str | None = None
    browser_zone: str | None = None

    # Market Research APIs
    tavily_api_key: str | None = None  # For market trends search (https://tavily.com/)
    serper_api_key: str | None = (
        None  # Alternative for market trends (https://serper.dev/)
    )
    zillow_api_key: str | None = None  # For price history (requires partnership)
    redfin_api_key: str | None = None  # For price history (requires partnership)

    # Web Scraping APIs
    scraperapi_key: str | None = (
        None  # Alternative to Bright Data (https://www.scraperapi.com/)
    )
    hasdata_api_key: str | None = (
        None  # HasData API for Zillow/Redfin scraping (https://api.hasdata.com/)
    )

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Application
    environment: str = "development"
    log_level: str = "INFO"
    log_file: str | None = (
        None  # If set, logs also to this file (e.g. logs/app.log). Default: backend/logs/app.log when enabled.
    )
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # LangSmith (env: LANGSMITH_TRACING, LANGSMITH_API_KEY, LANGSMITH_PROJECT, LANGSMITH_ENDPOINT)
    langsmith_tracing: bool = False
    langsmith_endpoint: str = "https://eu.api.smith.langchain.com"
    langsmith_api_key: str | None = None
    langsmith_project: str = "real-estate-ai-deep-agents"

    # Langfuse (LLM observability; optional)
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str = "https://cloud.langfuse.com"

    # PostgreSQL (for persistent checkpoints; optional – fallback to in-memory if not set)
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "real_estate_agent"
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_pool_size: int = 5
    postgres_max_overflow: int = 10

    # Auth (Phase 2 – JWT; optional)
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_days: int = 30

    # Pydantic v2: use SettingsConfigDict instead of class Config
    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),  # absolute path for langgraph dev from project root
        case_sensitive=False,
        extra="ignore",  # ignore unknown env vars (e.g. LANGFUSE_BASE_URL typo)
    )


settings = Settings()
