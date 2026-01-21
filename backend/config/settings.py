"""Application configuration settings."""
from pydantic_settings import BaseSettings
from typing import List
import os
from pathlib import Path

# Get the backend directory (where this file is located)
# __file__ is: backend/config/settings.py
# .parent is: backend/config
# .parent.parent is: backend
BACKEND_DIR = Path(__file__).parent.parent.resolve()  # Use resolve() to get absolute path
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # LLM Configuration
    # OpenRouter (default) - Unified API for 300+ models from multiple providers
    openrouter_api_key: str | None = None  # Default provider (get from https://openrouter.ai/keys)
    openrouter_model: str = "openai/gpt-4o-mini"  # Default model (can be: openai/gpt-4o, anthropic/claude-3.5-sonnet, etc.)
    openrouter_base_url: str = "https://openrouter.ai/api/v1"  # OpenRouter API endpoint
    
    # Ollama (local, no API key needed)
    ollama_base_url: str = "http://localhost:11434"  # Local Ollama server
    ollama_api_key: str | None = None  # Optional API key for remote Ollama
    ollama_model: str = "llama3.2"  # Default Ollama model (can be: llama3.2, qwen2.5, mistral, etc.)
    
    # Alternative providers
    openai_api_key: str | None = None  # Direct OpenAI (for gpt-oss-20b)
    groq_api_key: str | None = None  # Groq provider
    anthropic_api_key: str | None = None  # Anthropic provider
    google_api_key: str | None = None  # Google provider
    
    default_model: str = "openrouter:openai/gpt-4o-mini"  # Default model (OpenRouter, unified API)
    
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
    serper_api_key: str | None = None  # Alternative for market trends (https://serper.dev/)
    zillow_api_key: str | None = None  # For price history (requires partnership)
    redfin_api_key: str | None = None  # For price history (requires partnership)
    
    # Web Scraping APIs
    scraperapi_key: str | None = None  # Alternative to Bright Data (https://www.scraperapi.com/)
    hasdata_api_key: str | None = None  # HasData API for Zillow/Redfin scraping (https://api.hasdata.com/)
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Application
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: List[str] = ["http://localhost:5173", "http://localhost:3000"]
    
    # LangSmith
    langchain_tracing_v2: bool = False
    langchain_endpoint: str = "https://api.smith.langchain.com"
    langchain_api_key: str | None = None
    langchain_project: str = "enterprise-real-estate-ai"
    
    class Config:
        # Use absolute path to ensure .env is found regardless of working directory
        # This is critical when langgraph dev runs from project root
        env_file = str(ENV_FILE)  # ENV_FILE is already absolute (from resolve())
        case_sensitive = False


settings = Settings()
