"""FastAPI application for Real Estate AI Deep Agents."""
from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import logging
import time
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from langchain_core.messages import BaseMessage
from agents.main_agent import get_main_agent
from config.settings import settings
from api.middleware import rate_limit_middleware, monitoring_middleware, error_handling_middleware
from api.schemas import (
    ChatRequest, ChatResponse, LangGraphChatResponse, PropertySearchRequest, PropertySearchResponse,
    HealthResponse, MetricsResponse
)
from utils.message_serializer import serialize_messages
from utils.monitoring import setup_langsmith, metrics_collector
from utils.cache import cached
from utils.token_counter import validate_token_limit

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Setup LangSmith tracing
setup_langsmith()

# Initialize FastAPI app
app = FastAPI(
    title="Real Estate AI Deep Agents",
    description="Enterprise-level real estate AI solution with DeepAgents and LangGraph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware (order matters - last added is first executed)
# Execution order: rate_limit -> monitoring -> error_handling
@app.middleware("http")
async def apply_rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting middleware (first)."""
    return await rate_limit_middleware(request, call_next)

@app.middleware("http")
async def apply_monitoring_middleware(request: Request, call_next):
    """Apply monitoring middleware (second)."""
    return await monitoring_middleware(request, call_next)

@app.middleware("http")
async def apply_error_handling_middleware(request: Request, call_next):
    """Apply error handling middleware (last, outermost)."""
    return await error_handling_middleware(request, call_next)


# Request/Response models are now in api.schemas


# Health check
@app.get("/health", response_model=HealthResponse, tags=["monitoring"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the health status of the application including Redis connection status.
    """
    from utils.cache import get_redis_client
    
    redis_status = "connected" if get_redis_client() else "disconnected"
    
    return HealthResponse(
        status="healthy",
        version="1.0.0",
        redis=redis_status,
        timestamp=time.time()
    )


# Metrics endpoint
@app.get("/metrics", response_model=MetricsResponse, tags=["monitoring"])
async def get_metrics():
    """
    Get application metrics.
    
    Returns comprehensive metrics including request counts, error rates, 
    response times, and cache performance.
    """
    metrics = metrics_collector.get_metrics()
    return MetricsResponse(**metrics)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Real Estate AI Deep Agents",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs"
    }


# Note: LangGraph Platform API endpoints are now provided by langgraph dev server
# Use 'langgraph dev' to get all endpoints automatically:
# - /assistants/{assistant_id}/threads
# - /assistants/{assistant_id}/threads/{thread_id}/runs
# - /assistants/{assistant_id}/threads/{thread_id}/runs/stream
# - /info, /threads/search, etc.
# See langgraph.json for configuration


# Main chat endpoint
@app.post(
    "/api/v1/chat",
    response_model=None,  # Will return different formats based on request
    tags=["chat"],
    summary="Chat with the real estate AI agent",
    description="Send a message to the AI agent and receive a response. The agent can search properties, analyze locations, calculate financial metrics, and generate reports. Returns LangGraph format by default (compatible with agent-chat-ui). Use ?format=legacy for backward-compatible format."
)
async def chat(request: ChatRequest, http_request: Request):
    """
    Main chat endpoint for interacting with the real estate AI agent.
    
    Args:
        request: Chat request with message and optional conversation_id
        
    Returns:
        Chat response with agent's reply and conversation_id
    """
    try:
        # Get or create conversation ID (needed for token estimation)
        conversation_id = request.conversation_id or f"thread_{int(time.time())}"
        
        # Check if using providers that don't need strict token limits
        # Ollama (local) and OpenRouter (high limits) don't need strict limits
        is_local = settings.default_model.startswith("ollama:")
        # OpenRouter has very high limits, so skip token limits for it
        is_openrouter = (
            settings.default_model.startswith("openrouter:") or
            settings.openrouter_api_key is not None
        )
        skip_token_limits = is_local or is_openrouter
        
        # Validate token limit only if enabled and not using providers with high/no limits
        # For local providers (Ollama) and OpenRouter (high limits), token limits are disabled
        # For providers with strict limits (Groq free tier), limits are enforced
        if settings.enable_token_limits and not skip_token_limits:
            is_valid, estimated_tokens, error_msg = validate_token_limit(
                request.message,
                settings.max_tokens_per_request,
                request.user_name,
                conversation_id
            )
            
            if not is_valid:
                logger.warning(
                    f"Token limit exceeded: {estimated_tokens} tokens "
                    f"(limit: {settings.max_tokens_per_request})"
                )
                raise HTTPException(
                    status_code=413,
                    detail={
                        "error": "Request too large",
                        "estimated_tokens": estimated_tokens,
                        "max_tokens": settings.max_tokens_per_request,
                        "message": error_msg,
                        "suggestion": f"Reduce message size by approximately {estimated_tokens - settings.max_tokens_per_request} tokens"
                    }
                )
            
            logger.debug(f"Request token estimate: {estimated_tokens} tokens (limit: {settings.max_tokens_per_request})")
        else:
            # Just log token estimate for Ollama (no limit enforcement)
            from utils.token_counter import estimate_message_tokens
            estimated_tokens = estimate_message_tokens(
                request.message,
                request.user_name,
                conversation_id,
                include_overhead=True
            )
            provider_type = "local (Ollama)" if is_local else "OpenRouter (high limits)"
            logger.debug(f"Request token estimate: {estimated_tokens} tokens (token limits disabled for {provider_type})")
        
        # Get the main agent
        agent = get_main_agent()
        
        # Prepare config for conversation memory
        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": 100
        }
        
        # Create initial state
        state = {
            "messages": [HumanMessage(content=request.message)]
        }
        
        # Add user name to context if provided
        if request.user_name:
            # Prepend user name to message for personalization
            state["messages"][0].content = f"[User Name: {request.user_name}]\n\n{request.message}"
        
        logger.info(f"Processing chat request for conversation {conversation_id}")
        
        # Invoke the agent
        result = agent.invoke(state, config=config)
        
        # Check if client wants legacy format (backward compatibility)
        format_param = http_request.query_params.get("format", "")
        use_legacy_format = format_param == "legacy"
        
        # Extract messages from result
        if result and "messages" in result and result["messages"]:
            all_messages = result["messages"]
            
            # Default to LangGraph format (for agent-chat-ui)
            if not use_legacy_format:
                serialized_messages = serialize_messages(all_messages)
                return LangGraphChatResponse(
                    messages=serialized_messages,
                    thread_id=conversation_id
                )
            
            # Legacy format (backward compatibility) - return only last message
            last_message = all_messages[-1]
            response_content = last_message.content if hasattr(last_message, 'content') else str(last_message)
            
            # Handle empty responses
            if not response_content or response_content.strip() == "":
                response_content = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
        else:
            # No messages - return appropriate format
            if not use_legacy_format:
                return LangGraphChatResponse(
                    messages=[],
                    thread_id=conversation_id
                )
            response_content = "No response generated. Please try again."
        
        # Return legacy format
        return ChatResponse(
            response=response_content,
            conversation_id=conversation_id,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}"
        )


# Property search endpoint (direct API access)
@app.post(
    "/api/v1/properties/search",
    response_model=PropertySearchResponse,
    tags=["properties"],
    summary="Direct property search",
    description="Search for properties directly without going through the agent. Returns raw property data."
)
async def search_properties(
    query: str = Body(..., embed=True),
    property_type: Optional[str] = Body(None, embed=True),
    location: Optional[str] = Body(None, embed=True),
    min_price: Optional[int] = Body(None, embed=True),
    max_price: Optional[int] = Body(None, embed=True),
    bedrooms: Optional[int] = Body(None, embed=True),
    bathrooms: Optional[int] = Body(None, embed=True),
):
    """
    Direct property search endpoint.
    
    This endpoint allows direct property searches without going through the agent.
    Useful for programmatic access or when you need raw property data.
    """
    try:
        from tools.realty_us import realty_us_search_buy
        
        # Build location string
        if not location:
            raise HTTPException(status_code=400, detail="Location is required")
        
        location_str = f"city:{location}" if not location.startswith("city:") else location
        
        # Build price range
        prices = None
        if min_price or max_price:
            min_str = str(min_price) if min_price else ""
            max_str = str(max_price) if max_price else ""
            prices = f"{min_str},{max_str}"
        
        # Call the tool directly
        result = realty_us_search_buy.invoke({
            "location": location_str,
            "propertyType": property_type,
            "prices": prices,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
        })
        
        return result
        
    except Exception as e:
        logger.error(f"Error in property search: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error searching properties: {str(e)}"
        )


# ============================================================================
# LangGraph Platform API Endpoints
# ============================================================================
# 
# All LangGraph Platform API endpoints are now provided by 'langgraph dev' server.
# 
# To use them:
# 1. Install: pip install -U "langgraph-cli[inmem]"
# 2. Run: langgraph dev
# 3. Server starts on http://localhost:2024
# 
# Endpoints automatically available:
# - /assistants/{assistant_id}/threads
# - /assistants/{assistant_id}/threads/{thread_id}/runs
# - /assistants/{assistant_id}/threads/{thread_id}/runs/stream
# - /info, /threads/search, etc.
# 
# See langgraph.json for configuration.
# ============================================================================


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower()
    )
