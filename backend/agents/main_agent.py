"""Main orchestrator agent using DeepAgents framework."""
from deepagents import create_deep_agent
# Updated for LangChain v1.0 - init_chat_model moved
try:
    from langchain_core.language_models import init_chat_model
except ImportError:
    # Fallback for older versions
    from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from backend.config.settings import settings
try:
    from langchain_ollama import ChatOllama
    OLLAMA_AVAILABLE = True
except ImportError:
    OLLAMA_AVAILABLE = False
    ChatOllama = None
from backend.config.prompts import MAIN_AGENT_SYSTEM_PROMPT
from backend.tools.realty_us import realty_us_search_buy, realty_us_search_rent
from backend.agents.subagents import get_subagents
from backend.backends.storage import get_backend
from backend.backends.memory import get_memory_paths
from backend.utils.monitoring import setup_langsmith
from backend.utils.logging_config import setup_logging
from backend.config.hitl_config import get_hitl_config
import logging

# Configure logging to console + file (so langgraph dev also writes to backend/logs/app.log)
setup_logging()
logger = logging.getLogger(__name__)


def create_main_agent():
    """
    Create the main orchestrator agent with DeepAgents framework.
    
    Returns:
        Compiled LangGraph StateGraph agent
    """
    # Setup LangSmith tracing
    setup_langsmith()
    
    # Initialize LLM (Priority: OpenRouter -> Ollama -> OpenAI -> Groq -> Anthropic -> Google)
    try:
        model = None
        model_initialized = False
        # Try OpenRouter first (default, unified API for 300+ models)
        if settings.openrouter_api_key:
            try:
                # OpenRouter uses OpenAI-compatible API, so we use langchain-openai with custom base_url
                from langchain_openai import ChatOpenAI
                openrouter_model = settings.openrouter_model
                model = ChatOpenAI(
                    model=openrouter_model,
                    api_key=settings.openrouter_api_key,
                    base_url=settings.openrouter_base_url,
                    default_headers={
                        "HTTP-Referer": "https://github.com/oelbourki",  # Optional: for analytics
                        "X-Title": "Real Estate AI Deep Agents"  # Optional: for analytics
                    }
                )
                logger.info(f"✅ Initialized OpenRouter model: {openrouter_model} at {settings.openrouter_base_url}")
                model_initialized = True
            except Exception as openrouter_error:
                logger.warning(f"⚠️  OpenRouter initialization failed: {openrouter_error}")
                logger.info("Falling back to other LLM providers...")
        
        # Try Ollama (local, no API key needed)
        elif model is None and OLLAMA_AVAILABLE:
            try:
                ollama_model_name = settings.ollama_model
                # Try direct ChatOllama first (more reliable)
                try:
                    model = ChatOllama(
                        model=ollama_model_name,
                        base_url=settings.ollama_base_url,
                    )
                    logger.info(f"✅ Initialized Ollama model: {ollama_model_name} at {settings.ollama_base_url}")
                    model_initialized = True
                except Exception as direct_error:
                    # Fallback to init_chat_model
                    try:
                        model = init_chat_model(
                            f"ollama:{ollama_model_name}",
                            base_url=settings.ollama_base_url,
                            api_key=settings.ollama_api_key  # Optional, only for remote Ollama
                        )
                        logger.info(f"✅ Initialized Ollama model: {ollama_model_name} at {settings.ollama_base_url}")
                        model_initialized = True
                    except Exception as init_error:
                        raise direct_error from init_error
            except Exception as ollama_error:
                logger.warning(
                    f"⚠️  Ollama not available at {settings.ollama_base_url}: {ollama_error}\n"
                    f"   To use Ollama (recommended, local, no API key needed):\n"
                    f"   1. Install Ollama: curl -fsSL https://ollama.com/install.sh | sh\n"
                    f"   2. Pull model: ollama pull {settings.ollama_model}\n"
                    f"   3. Start server: ollama serve\n"
                    f"   4. Install langchain-ollama: pip install langchain-ollama\n"
                    f"   Falling back to other LLM providers..."
                )
        else:
            logger.warning(
                f"⚠️  langchain-ollama package not installed. Install with: pip install langchain-ollama\n"
                f"   Falling back to other LLM providers..."
            )
        
        # Fallback to other providers if Ollama not available
        if not model_initialized:
            if settings.openai_api_key:
                try:
                    openai_model = settings.default_model if "openai:" in settings.default_model else "openai:gpt-oss-20b"
                    model = init_chat_model(
                        openai_model,
                        api_key=settings.openai_api_key
                    )
                    logger.info(f"Initialized OpenAI model: {openai_model}")
                    model_initialized = True
                except Exception as e:
                    logger.warning(f"OpenAI initialization failed: {e}")
            
            if not model_initialized and settings.groq_api_key:
                try:
                    groq_model = "groq:qwen/qwen3-32b"  # Default Groq model
                    model = init_chat_model(
                        groq_model,
                        api_key=settings.groq_api_key
                    )
                    logger.info(f"Initialized Groq model: {groq_model}")
                    model_initialized = True
                except Exception as e:
                    logger.warning(f"Groq initialization failed: {e}")
            
            if not model_initialized and settings.anthropic_api_key:
                try:
                    model = init_chat_model(
                        "anthropic:claude-sonnet-4-5-20250929",
                        api_key=settings.anthropic_api_key
                    )
                    logger.info("Initialized Anthropic Claude model")
                    model_initialized = True
                except Exception as e:
                    logger.warning(f"Anthropic initialization failed: {e}")
            
            if not model_initialized and settings.google_api_key:
                try:
                    model = init_chat_model(
                        "google:gemini-2.0-flash-exp",
                        api_key=settings.google_api_key
                    )
                    logger.info("Initialized Google Gemini model")
                    model_initialized = True
                except Exception as e:
                    logger.warning(f"Google initialization failed: {e}")
        
        # If no model was initialized, raise error
        if not model_initialized:
            raise ValueError(
                "No LLM provider available. Options:\n"
                "1. Set OPENROUTER_API_KEY for OpenRouter (recommended, default): https://openrouter.ai/keys\n"
                "   - Access to 300+ models from OpenAI, Anthropic, Google, etc.\n"
                "   - Set OPENROUTER_MODEL to choose model (e.g., openai/gpt-4o-mini)\n"
                "2. Install and run Ollama locally: https://ollama.com\n"
                "   - Run: ollama pull llama3.2\n"
                "   - Start: ollama serve\n"
                "3. Set OPENAI_API_KEY for OpenAI\n"
                "4. Set GROQ_API_KEY for Groq\n"
                "5. Set ANTHROPIC_API_KEY for Anthropic\n"
                "6. Set GOOGLE_API_KEY for Google"
            )
    except Exception as e:
        logger.error(f"Failed to initialize LLM: {e}", exc_info=True)
        raise
    
    # Real estate tools (direct tools for simple queries)
    tools = [
        realty_us_search_buy,
        realty_us_search_rent,
    ]
    logger.info(f"Loaded {len(tools)} direct tools")
    
    # Get subagents (Phase 2)
    subagents = get_subagents()
    logger.info(f"Loaded {len(subagents)} subagents")
    
    # Create backend (Phase 3: Composite backend with filesystem)
    backend = get_backend()
    
    # Create checkpointer for conversation memory
    checkpointer = MemorySaver()
    
    # Get HITL configuration (Phase 4)
    interrupt_on = get_hitl_config()
    
    # Create the deep agent
    try:
        agent = create_deep_agent(
            model=model,
            system_prompt=MAIN_AGENT_SYSTEM_PROMPT,
            tools=tools,
            backend=backend,
            checkpointer=checkpointer,
            subagents=subagents,  # Phase 3: 6 subagents enabled
            memory=get_memory_paths(),  # Long-term memory (Phase 3)
            interrupt_on=interrupt_on,  # Phase 4: HITL workflows
        )

        logger.info("Main agent created successfully with subagents and HITL")
        return agent
    except Exception as e:
        logger.error(f"Failed to create deep agent: {e}", exc_info=True)
        raise


# Global agent instance (lazy initialization)
_main_agent = None


def get_main_agent():
    """Get or create the main agent instance."""
    global _main_agent
    if _main_agent is None:
        _main_agent = create_main_agent()
    return _main_agent
