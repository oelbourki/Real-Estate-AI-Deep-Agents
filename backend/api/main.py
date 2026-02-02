"""FastAPI application for Real Estate AI Deep Agents."""

import asyncio
import json
import logging
import time
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from langchain_core.messages import HumanMessage

from agents.main_agent import get_main_agent, create_main_agent_with_checkpointer
from config.settings import settings
from api.middleware import (
    rate_limit_middleware,
    monitoring_middleware,
    error_handling_middleware,
)
from api.schemas import (
    ChatRequest,
    ChatResponse,
    LangGraphChatResponse,
    PropertySearchResponse,
    HealthResponse,
    MetricsResponse,
    RunCreateRequest,
    RunResponse,
    ThreadCreateResponse,
    ThreadListResponse,
    PlatformInfoResponse,
    PlatformThreadCreateRequest,
    PlatformThreadResponse,
    PlatformThreadSearchRequest,
    PlatformRunCreateRequest,
    PlatformThreadHistoryRequest,
)
from utils.message_serializer import serialize_messages
from utils.monitoring import setup_langsmith, metrics_collector
from utils.token_counter import validate_token_limit
from utils.logging_config import setup_logging
from utils.postgres_checkpoint import create_postgres_checkpointer
from api.auth import (
    router as auth_router,
    get_current_session_optional,
    get_current_user_optional,
)
from fastapi import Depends

# Configure logging (console + file)
setup_logging()
logger = logging.getLogger(__name__)

# Setup LangSmith tracing
setup_langsmith()


def _get_langfuse_handler():
    """Return Langfuse CallbackHandler if configured, else None."""
    if not (settings.langfuse_public_key and settings.langfuse_secret_key):
        return None
    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler(
            public_key=settings.langfuse_public_key,
            secret_key=settings.langfuse_secret_key,
            host=settings.langfuse_host,
        )
    except Exception as e:
        logger.debug("Langfuse CallbackHandler not available: %s", e)
        return None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: create async graph with Postgres checkpointer when configured. Shutdown: flush Langfuse, close pool."""
    app.state.agent_async = None
    app.state.postgres_pool = None
    app.state.postgres_configured_but_failed = False
    app.state.langfuse = None

    # Optional: init Langfuse client for flush on shutdown
    if settings.langfuse_public_key and settings.langfuse_secret_key:
        try:
            from langfuse import Langfuse

            app.state.langfuse = Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            )
            logger.info("Langfuse initialized")
        except ImportError:
            logger.info(
                "Langfuse not installed (pip install langfuse); tracing disabled"
            )
        except Exception as e:
            logger.warning("Langfuse init failed: %s", e)

    # Optional: Postgres checkpointer + async graph
    from utils.postgres_checkpoint import is_postgres_configured

    app.state.postgres_configured_but_failed = False
    pool, checkpointer = await create_postgres_checkpointer()
    if checkpointer is not None:
        app.state.postgres_pool = pool
        try:
            app.state.agent_async = create_main_agent_with_checkpointer(checkpointer)
            logger.info("Async agent with PostgreSQL checkpointer ready")
        except Exception as e:
            logger.error("Failed to create async agent: %s", e, exc_info=True)
            if pool:
                await pool.close()
    elif is_postgres_configured():
        app.state.postgres_configured_but_failed = True

    yield

    # Shutdown
    if getattr(app.state, "langfuse", None):
        try:
            app.state.langfuse.flush()
        except Exception as e:
            logger.debug("Langfuse flush: %s", e)
    if getattr(app.state, "postgres_pool", None):
        try:
            await app.state.postgres_pool.close()
        except Exception as e:
            logger.debug("Postgres pool close: %s", e)


# Initialize FastAPI app
app = FastAPI(
    title="Real Estate AI Deep Agents",
    description="Enterprise-level real estate AI solution with DeepAgents and LangGraph",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth router (Phase 2): /api/v1/auth/register, /login, /session, /sessions, etc.
app.include_router(auth_router, prefix="/api/v1")


# Custom middleware (order matters - last added is first executed)
# Execution order: security_headers -> rate_limit -> monitoring -> error_handling
@app.middleware("http")
async def apply_security_headers_middleware(request: Request, call_next):
    """Apply security headers (X-Content-Type-Options, X-Frame-Options, HSTS in prod)."""
    from api.middleware import security_headers_middleware

    return await security_headers_middleware(request, call_next)


@app.middleware("http")
async def apply_rate_limit_middleware(request: Request, call_next):
    """Apply rate limiting middleware."""
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

    Returns the health status of the application including Redis and PostgreSQL status.
    """
    from utils.cache import get_redis_client

    redis_status = "connected" if get_redis_client() else "disconnected"

    postgres_status = "unconfigured"
    if getattr(app.state, "postgres_configured_but_failed", False):
        postgres_status = "disconnected"
    elif getattr(app.state, "postgres_pool", None):
        try:
            async with app.state.postgres_pool.connection() as conn:
                async with conn.cursor() as cur:
                    await cur.execute("SELECT 1")
            postgres_status = "connected"
        except Exception:
            postgres_status = "disconnected"

    return HealthResponse(
        status="healthy",
        version="1.0.0",
        environment=settings.environment,
        redis=redis_status,
        postgres=postgres_status,
        timestamp=time.time(),
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
        "docs": "/docs",
    }


# ---------------------------------------------------------------------------
# LangGraph Platform API compatibility (agent-chat-ui)
# Same paths and request/response shape as langgraph dev so the UI works.
# ---------------------------------------------------------------------------


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


@app.get(
    "/info",
    response_model=PlatformInfoResponse,
    tags=["langgraph-platform"],
    summary="Server info (LangGraph Platform)",
)
async def platform_info():
    """GET /info - agent-chat-ui uses this to check server is up."""
    try:
        import langgraph

        lg_version = getattr(langgraph, "__version__", "")
    except ImportError:
        lg_version = ""
    return PlatformInfoResponse(
        version="1.0.0",
        langgraph_py_version=lg_version,
        flags={},
        metadata={"server": "fastapi"},
    )


@app.post(
    "/threads",
    response_model=PlatformThreadResponse,
    tags=["langgraph-platform"],
    summary="Create thread (LangGraph Platform)",
)
async def platform_create_thread(body: PlatformThreadCreateRequest):
    """POST /threads - create a thread. Returns thread_id for runs."""
    thread_id = body.thread_id or str(uuid.uuid4())
    now = _now_iso()
    return PlatformThreadResponse(
        thread_id=thread_id,
        created_at=now,
        updated_at=now,
        metadata=body.metadata or {},
        status="idle",
        config={},
        values={},
        interrupts={},
    )


@app.post(
    "/threads/search",
    response_model=list,
    tags=["langgraph-platform"],
    summary="Search threads (LangGraph Platform)",
)
async def platform_search_threads(body: PlatformThreadSearchRequest):
    """POST /threads/search - list threads. Without auth we return []; with auth returns user sessions."""

    # Optional: could add optional auth and return user's session IDs as threads
    thread_ids: list[str] = []
    # For now return empty list (no per-user thread list without auth)
    now = _now_iso()
    return [
        PlatformThreadResponse(
            thread_id=tid,
            created_at=now,
            updated_at=now,
            metadata={},
            status="idle",
            config={},
            values={},
            interrupts={},
        ).model_dump()
        for tid in thread_ids[: body.limit]
    ]


@app.get(
    "/threads/{thread_id}/state",
    tags=["langgraph-platform"],
    summary="Get thread state (LangGraph Platform)",
)
async def platform_get_thread_state(thread_id: str):
    """GET /threads/{id}/state - minimal state. Full state would require checkpointer read."""
    now = _now_iso()
    return {
        "thread_id": thread_id,
        "created_at": now,
        "updated_at": now,
        "metadata": {},
        "status": "idle",
        "config": {},
        "values": {"messages": []},
        "interrupts": {},
    }


@app.post(
    "/threads/{thread_id}/history",
    response_model=list,
    tags=["langgraph-platform"],
    summary="Get thread history (LangGraph Platform)",
)
async def platform_thread_history(
    thread_id: str,
    body: Optional[PlatformThreadHistoryRequest] = Body(default=None),
):
    """POST /threads/{id}/history - return past states for thread. agent-chat-ui uses this when fetchStateHistory is true."""
    if body is None:
        body = PlatformThreadHistoryRequest()
    agent_async = getattr(app.state, "agent_async", None)
    if agent_async is None:
        return []
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state_snapshot = await agent_async.aget_state(config)
    except Exception as e:
        logger.debug("Thread history aget_state failed for %s: %s", thread_id, e)
        return []
    if state_snapshot is None or not state_snapshot.values:
        return []
    values = state_snapshot.values
    messages = values.get("messages") if isinstance(values, dict) else []
    if not messages:
        return []
    serialized = serialize_messages(messages)
    now = _now_iso()
    checkpoint_id = ""
    config_attr = getattr(state_snapshot, "config", None) or {}
    configurable = (
        config_attr.get("configurable", {}) if isinstance(config_attr, dict) else {}
    )
    if isinstance(configurable, dict) and configurable.get("checkpoint_id"):
        checkpoint_id = str(configurable["checkpoint_id"])
    elif hasattr(state_snapshot, "checkpoint_id") and state_snapshot.checkpoint_id:
        checkpoint_id = str(state_snapshot.checkpoint_id)
    elif hasattr(state_snapshot, "checkpoint") and state_snapshot.checkpoint:
        c = state_snapshot.checkpoint
        checkpoint_id = str(c.get("id", c) if isinstance(c, dict) else c)
    created_at_val = getattr(state_snapshot, "created_at", None) or now
    if hasattr(created_at_val, "isoformat"):
        created_at_val = created_at_val.isoformat()
    elif not isinstance(created_at_val, str):
        created_at_val = now

    thread_state = {
        "values": {"messages": serialized},
        "next": getattr(state_snapshot, "next", []) or [],
        "tasks": getattr(state_snapshot, "tasks", []) or [],
        "checkpoint": {
            "thread_id": thread_id,
            "checkpoint_ns": "",
            "checkpoint_id": checkpoint_id,
        },
        "metadata": getattr(state_snapshot, "metadata", {}) or {},
        "created_at": created_at_val,
    }
    return [thread_state]


@app.get(
    "/threads/{thread_id}/runs",
    tags=["langgraph-platform"],
    summary="List runs (LangGraph Platform)",
)
async def platform_list_runs(thread_id: str, limit: int = 10, offset: int = 0):
    """GET /threads/{id}/runs - we don't store run IDs; return empty list."""
    return []


def _platform_run_input_to_state(platform_body: PlatformRunCreateRequest) -> dict:
    """Build graph state from Platform run input (input.messages or input.message)."""
    from langchain_core.messages import AIMessage, HumanMessage

    inp = platform_body.input or {}
    messages = inp.get("messages")
    if messages and isinstance(messages, list):
        out = []
        for m in messages:
            if isinstance(m, dict):
                role = (m.get("role") or m.get("type") or "user").lower()
                content = m.get("content", "") or ""
                if role in ("user", "human"):
                    out.append(HumanMessage(content=content))
                elif role in ("assistant", "ai"):
                    out.append(AIMessage(content=content))
                else:
                    out.append(HumanMessage(content=content))
            else:
                out.append(HumanMessage(content=str(m)))
        return {"messages": out}
    msg = (inp.get("message") or "").strip() or "Hello"
    return {"messages": [HumanMessage(content=msg)]}


@app.post(
    "/threads/{thread_id}/runs/stream",
    response_class=StreamingResponse,
    tags=["langgraph-platform"],
    summary="Create run and stream (LangGraph Platform)",
)
async def platform_runs_stream(thread_id: str, body: PlatformRunCreateRequest):
    """POST /threads/{id}/runs/stream - stream agent response. Same as /api/v1/threads/{id}/runs/stream with Platform body."""
    agent_async = getattr(app.state, "agent_async", None)
    if agent_async is None:
        raise HTTPException(
            status_code=503,
            detail="Streaming requires PostgreSQL checkpointer. Set POSTGRES_* env vars.",
        )
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": (body.config or {}).get("recursion_limit", 100),
    }
    if body.config and "configurable" in body.config:
        config["configurable"].update(body.config["configurable"])
    langfuse_handler = _get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
    state = _platform_run_input_to_state(body)

    async def event_stream():
        try:
            async for event in agent_async.astream(
                state, config=config, stream_mode="messages"
            ):
                msg = (
                    event[0] if isinstance(event, tuple) and len(event) >= 1 else event
                )
                if hasattr(msg, "content") and msg.content:
                    chunk = (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                    yield f"data: {json.dumps({'type': 'message', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\n\n"
        except Exception as e:
            logger.error("Platform run stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post(
    "/threads/{thread_id}/runs/wait",
    tags=["langgraph-platform"],
    summary="Create run and wait (LangGraph Platform)",
)
async def platform_runs_wait(thread_id: str, body: PlatformRunCreateRequest):
    """POST /threads/{id}/runs/wait - run agent and return full state."""
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": (body.config or {}).get("recursion_limit", 100),
    }
    if body.config and "configurable" in body.config:
        config["configurable"].update(body.config["configurable"])
    langfuse_handler = _get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
    state = _platform_run_input_to_state(body)

    agent_async = getattr(app.state, "agent_async", None)
    if agent_async is not None:
        result = await agent_async.ainvoke(state, config=config)
    else:
        agent = get_main_agent()
        result = await asyncio.to_thread(agent.invoke, state, config=config)

    if not result or "messages" not in result:
        return {"values": {"messages": []}, "thread_id": thread_id}
    serialized = serialize_messages(result["messages"])
    return {"values": {"messages": serialized}, "thread_id": thread_id}


# Main chat endpoint
@app.post(
    "/api/v1/chat",
    response_model=None,  # Will return different formats based on request
    tags=["chat"],
    summary="Chat with the real estate AI agent",
    description="Send a message to the AI agent and receive a response. The agent can search properties, analyze locations, calculate financial metrics, and generate reports. Returns LangGraph format by default (compatible with agent-chat-ui). Use ?format=legacy for backward-compatible format.",
)
async def chat(
    request: ChatRequest,
    http_request: Request,
    session: Optional[Any] = Depends(get_current_session_optional),
):
    """
    Main chat endpoint for interacting with the real estate AI agent.
    If Authorization header has a valid session JWT, thread_id = session.id; else uses conversation_id from body.
    """
    try:
        # Use session.id as thread_id when auth session is present
        conversation_id = (
            (session.id if session else None)
            or request.conversation_id
            or f"thread_{int(time.time())}"
        )

        # Check if using providers that don't need strict token limits
        # Ollama (local) and OpenRouter (high limits) don't need strict limits
        is_local = settings.default_model.startswith("ollama:")
        # OpenRouter has very high limits, so skip token limits for it
        is_openrouter = (
            settings.default_model.startswith("openrouter:")
            or settings.openrouter_api_key is not None
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
                conversation_id,
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
                        "suggestion": f"Reduce message size by approximately {estimated_tokens - settings.max_tokens_per_request} tokens",
                    },
                )

            logger.debug(
                f"Request token estimate: {estimated_tokens} tokens (limit: {settings.max_tokens_per_request})"
            )
        else:
            # Just log token estimate for Ollama (no limit enforcement)
            from utils.token_counter import estimate_message_tokens

            estimated_tokens = estimate_message_tokens(
                request.message,
                request.user_name,
                conversation_id,
                include_overhead=True,
            )
            provider_type = "local (Ollama)" if is_local else "OpenRouter (high limits)"
            logger.debug(
                f"Request token estimate: {estimated_tokens} tokens (token limits disabled for {provider_type})"
            )

        # Prepare config for conversation memory
        config = {
            "configurable": {"thread_id": conversation_id},
            "recursion_limit": 100,
        }
        langfuse_handler = _get_langfuse_handler()
        if langfuse_handler:
            config["callbacks"] = [langfuse_handler]

        # Create initial state
        state = {"messages": [HumanMessage(content=request.message)]}

        # Add user name to context if provided
        if request.user_name:
            # Prepend user name to message for personalization
            state["messages"][
                0
            ].content = f"[User Name: {request.user_name}]\n\n{request.message}"

        logger.info(f"Processing chat request for conversation {conversation_id}")

        # Invoke: use async agent with Postgres when available, else sync in-memory in thread
        agent_async = getattr(app.state, "agent_async", None)
        if agent_async is not None:
            result = await agent_async.ainvoke(state, config=config)
        else:
            agent = get_main_agent()
            result = await asyncio.to_thread(agent.invoke, state, config=config)

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
                    messages=serialized_messages, thread_id=conversation_id
                )

            # Legacy format (backward compatibility) - return only last message
            last_message = all_messages[-1]
            response_content = (
                last_message.content
                if hasattr(last_message, "content")
                else str(last_message)
            )

            # Handle empty responses
            if not response_content or response_content.strip() == "":
                response_content = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
        else:
            # No messages - return appropriate format
            if not use_legacy_format:
                return LangGraphChatResponse(messages=[], thread_id=conversation_id)
            response_content = "No response generated. Please try again."

        # Return legacy format
        return ChatResponse(
            response=response_content,
            conversation_id=conversation_id,
            timestamp=time.time(),
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while processing your request: {str(e)}",
        )


# Streaming chat endpoint (requires async agent with Postgres checkpointer)
@app.post(
    "/api/v1/chat/stream",
    response_class=StreamingResponse,
    tags=["chat"],
    summary="Chat with the agent (streaming)",
    description="Stream the agent response as server-sent events. Requires PostgreSQL checkpointer.",
)
async def chat_stream(
    request: ChatRequest,
    http_request: Request,
    session: Optional[Any] = Depends(get_current_session_optional),
):
    """Stream chat response as SSE. If Authorization has session JWT, thread_id = session.id."""
    conversation_id = (
        (session.id if session else None)
        or request.conversation_id
        or f"thread_{int(time.time())}"
    )

    # Token limit validation (same as chat)
    is_local = settings.default_model.startswith("ollama:")
    is_openrouter = (
        settings.default_model.startswith("openrouter:")
        or settings.openrouter_api_key is not None
    )
    skip_token_limits = is_local or is_openrouter
    if settings.enable_token_limits and not skip_token_limits:
        is_valid, estimated_tokens, error_msg = validate_token_limit(
            request.message,
            settings.max_tokens_per_request,
            request.user_name,
            conversation_id,
        )
        if not is_valid:
            raise HTTPException(
                status_code=413,
                detail={
                    "error": "Request too large",
                    "estimated_tokens": estimated_tokens,
                    "max_tokens": settings.max_tokens_per_request,
                    "message": error_msg,
                },
            )

    agent_async = getattr(app.state, "agent_async", None)
    if agent_async is None:
        raise HTTPException(
            status_code=503,
            detail="Streaming requires PostgreSQL checkpointer. Set POSTGRES_* env vars.",
        )
    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": 100,
    }
    langfuse_handler = _get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]

    message_content = request.message
    if request.user_name:
        message_content = f"[User Name: {request.user_name}]\n\n{request.message}"
    state = {"messages": [HumanMessage(content=message_content)]}

    async def event_stream():
        try:
            async for event in agent_async.astream(
                state, config=config, stream_mode="messages"
            ):
                # LangGraph stream_mode="messages": event is (message, metadata) or (node, message, metadata)
                msg = (
                    event[0] if isinstance(event, tuple) and len(event) >= 1 else event
                )
                if hasattr(msg, "content") and msg.content:
                    chunk = (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                    yield f"data: {json.dumps({'type': 'message', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'thread_id': conversation_id})}\n\n"
        except Exception as e:
            logger.error("Stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Thread / Run API (Phase 3 – compatible with langgraph dev semantics)
# ---------------------------------------------------------------------------


def _run_input_to_state(body: RunCreateRequest) -> dict:
    """Build graph state from RunCreateRequest.input (message or messages)."""
    from langchain_core.messages import AIMessage, HumanMessage

    inp = body.input
    if inp.messages:
        messages = []
        for m in inp.messages:
            role = (m.get("role") or m.get("type") or "user").lower()
            content = m.get("content", "") or ""
            if role in ("user", "human"):
                messages.append(HumanMessage(content=content))
            elif role in ("assistant", "ai"):
                messages.append(AIMessage(content=content))
            else:
                messages.append(HumanMessage(content=content))
        return {"messages": messages}
    message = (inp.message or "").strip() or "Hello"
    return {"messages": [HumanMessage(content=message)]}


@app.post(
    "/api/v1/threads",
    response_model=ThreadCreateResponse,
    tags=["threads"],
    summary="Create a thread",
    description="Create a new conversation thread. Returns thread_id for use in runs.",
)
async def create_thread():
    """Create a new thread (UUID). With auth (Phase 2), thread will be scoped to user/session."""
    return ThreadCreateResponse(thread_id=str(uuid.uuid4()))


@app.get(
    "/api/v1/threads",
    response_model=ThreadListResponse,
    tags=["threads"],
    summary="List threads",
    description="List thread IDs. With auth (Bearer session or user token), returns threads for the current user.",
)
async def list_threads(
    session: Optional[Any] = Depends(get_current_session_optional),
    user: Optional[Any] = Depends(get_current_user_optional),
):
    """List threads. With auth (session or user token) returns that user's session IDs."""
    from services.database import database_service

    user_id = None
    if session:
        user_id = session.user_id
    elif user:
        user_id = user.id
    if user_id is not None:
        sessions = database_service.get_user_sessions(user_id)
        return ThreadListResponse(thread_ids=[s.id for s in sessions])
    return ThreadListResponse(thread_ids=[])


@app.post(
    "/api/v1/threads/{thread_id}/runs",
    response_model=RunResponse,
    tags=["threads"],
    summary="Run agent on a thread",
    description='Invoke the agent for the given thread. Body: { "input": { "message": "..." } } or { "input": { "messages": [...] } }.',
)
async def create_run(thread_id: str, body: RunCreateRequest):
    """Execute a run on the thread. Uses async agent when Postgres is configured."""
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }
    langfuse_handler = _get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
    state = _run_input_to_state(body)

    agent_async = getattr(app.state, "agent_async", None)
    if agent_async is not None:
        result = await agent_async.ainvoke(state, config=config)
    else:
        agent = get_main_agent()
        result = await asyncio.to_thread(agent.invoke, state, config=config)

    if not result or "messages" not in result:
        return RunResponse(messages=[], thread_id=thread_id)
    serialized = serialize_messages(result["messages"])
    return RunResponse(messages=serialized, thread_id=thread_id)


@app.post(
    "/api/v1/threads/{thread_id}/runs/stream",
    response_class=StreamingResponse,
    tags=["threads"],
    summary="Stream a run",
    description="Stream the agent response for the given thread. Requires PostgreSQL checkpointer.",
)
async def create_run_stream(thread_id: str, body: RunCreateRequest):
    """Stream a run. Requires async agent (Postgres)."""
    agent_async = getattr(app.state, "agent_async", None)
    if agent_async is None:
        raise HTTPException(
            status_code=503,
            detail="Streaming runs require PostgreSQL checkpointer. Set POSTGRES_* env vars.",
        )
    config = {
        "configurable": {"thread_id": thread_id},
        "recursion_limit": 100,
    }
    langfuse_handler = _get_langfuse_handler()
    if langfuse_handler:
        config["callbacks"] = [langfuse_handler]
    state = _run_input_to_state(body)

    async def event_stream():
        try:
            async for event in agent_async.astream(
                state, config=config, stream_mode="messages"
            ):
                msg = (
                    event[0] if isinstance(event, tuple) and len(event) >= 1 else event
                )
                if hasattr(msg, "content") and msg.content:
                    chunk = (
                        msg.content
                        if isinstance(msg.content, str)
                        else str(msg.content)
                    )
                    yield f"data: {json.dumps({'type': 'message', 'content': chunk})}\n\n"
            yield f"data: {json.dumps({'type': 'done', 'thread_id': thread_id})}\n\n"
        except Exception as e:
            logger.error("Run stream error: %s", e, exc_info=True)
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# Property search endpoint (direct API access)
@app.post(
    "/api/v1/properties/search",
    response_model=PropertySearchResponse,
    tags=["properties"],
    summary="Direct property search",
    description="Search for properties directly without going through the agent. Returns raw property data.",
)
async def search_properties(
    location: str = Body(
        ..., embed=True, description="Search location (e.g. 'San Francisco, CA')"
    ),
    property_type: Optional[str] = Body(None, embed=True),
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

        location_str = (
            f"city:{location}" if not location.startswith("city:") else location
        )

        # Build price range
        prices = None
        if min_price or max_price:
            min_str = str(min_price) if min_price else ""
            max_str = str(max_price) if max_price else ""
            prices = f"{min_str},{max_str}"

        # Call the tool directly
        result = realty_us_search_buy.invoke(
            {
                "location": location_str,
                "propertyType": property_type,
                "prices": prices,
                "bedrooms": bedrooms,
                "bathrooms": bathrooms,
            }
        )

        return result

    except Exception as e:
        logger.error(f"Error in property search: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Error searching properties: {str(e)}"
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
        log_level=settings.log_level.lower(),
    )
