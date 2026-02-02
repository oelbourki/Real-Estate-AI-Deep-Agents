"""API request/response schemas for OpenAPI documentation."""

import re
from datetime import datetime
from typing import Optional, List, Dict, Any

from pydantic import BaseModel, Field, EmailStr, SecretStr, field_validator


class ChatRequest(BaseModel):
    """Chat request schema."""

    message: str = Field(..., description="User message to the agent")
    conversation_id: Optional[str] = Field(
        None, description="Conversation ID for context (optional)"
    )
    user_name: Optional[str] = Field(
        None, description="User name for personalization (optional)"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "message": "Find 3 bedroom houses in San Francisco under $2M",
                "user_name": "John",
            }
        }


class ChatResponse(BaseModel):
    """Chat response schema (backward compatible format)."""

    response: str = Field(..., description="Agent's response")
    conversation_id: str = Field(..., description="Conversation ID for this session")
    timestamp: float = Field(..., description="Response timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "response": "I found 5 properties matching your criteria...",
                "conversation_id": "thread_1234567890",
                "timestamp": 1706359845.123,
            }
        }


class LangGraphChatResponse(BaseModel):
    """LangGraph-compatible chat response schema for agent-chat-ui."""

    messages: List[Dict[str, Any]] = Field(
        ..., description="List of messages in LangGraph format"
    )
    thread_id: str = Field(..., description="Thread/conversation ID")

    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "type": "human",
                        "role": "user",
                        "content": "Find houses in San Francisco",
                    },
                    {
                        "type": "ai",
                        "role": "assistant",
                        "content": "I found several properties...",
                    },
                ],
                "thread_id": "thread_1234567890",
            }
        }


class PropertySearchRequest(BaseModel):
    """Property search request schema."""

    location: str = Field(
        ..., description="Location to search (e.g., 'San Francisco, CA')"
    )
    property_type: Optional[str] = Field(None, description="Property type filter")
    min_price: Optional[int] = Field(None, description="Minimum price")
    max_price: Optional[int] = Field(None, description="Maximum price")
    bedrooms: Optional[int] = Field(None, description="Number of bedrooms")
    bathrooms: Optional[int] = Field(None, description="Number of bathrooms")

    class Config:
        json_schema_extra = {
            "example": {
                "location": "San Francisco, CA",
                "property_type": "single_family_home",
                "min_price": 500000,
                "max_price": 2000000,
                "bedrooms": 3,
                "bathrooms": 2,
            }
        }


class PropertySearchResponse(BaseModel):
    """Property search response schema."""

    results: List[Dict[str, Any]] = Field(..., description="List of properties")
    total: int = Field(..., description="Total number of results")

    class Config:
        json_schema_extra = {
            "example": {
                "results": [
                    {
                        "address": "123 Main St, San Francisco, CA",
                        "price": 1500000,
                        "beds": 3,
                        "baths": 2,
                    }
                ],
                "total": 1,
            }
        }


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    environment: str = Field(
        ..., description="Environment (development, staging, production)"
    )
    redis: str = Field(..., description="Redis connection status")
    postgres: Optional[str] = Field(
        None,
        description="PostgreSQL checkpointer status (connected/disconnected/unconfigured)",
    )
    timestamp: float = Field(..., description="Check timestamp")


class MetricsResponse(BaseModel):
    """Metrics response schema."""

    requests_total: int
    requests_by_endpoint: Dict[str, Dict[str, Any]]
    errors_total: int
    errors_by_type: Dict[str, int]
    avg_response_time: float
    cache_hits: int
    cache_misses: int
    cache_hit_rate: float
    error_rate: float


# Thread/Run API (Phase 3 – compatible with langgraph dev semantics)
class ThreadCreateResponse(BaseModel):
    """Response after creating a thread."""

    thread_id: str = Field(..., description="Thread ID for subsequent runs")


class ThreadListResponse(BaseModel):
    """List of thread IDs (scoped by auth when implemented)."""

    thread_ids: List[str] = Field(default_factory=list, description="Thread IDs")


class RunInput(BaseModel):
    """Input for a run: single message or list of messages."""

    message: Optional[str] = Field(
        None, description="Single user message (converted to messages)"
    )
    messages: Optional[List[Dict[str, Any]]] = Field(
        None, description="Full message list in OpenAI format"
    )


class RunCreateRequest(BaseModel):
    """Request body for POST /threads/{thread_id}/runs and .../runs/stream."""

    input: RunInput = Field(..., description="Run input (message or messages)")


class RunResponse(BaseModel):
    """Response from a run (same shape as LangGraph chat)."""

    messages: List[Dict[str, Any]] = Field(
        ..., description="Messages in LangGraph format"
    )
    thread_id: str = Field(..., description="Thread ID")


# ---------------------------------------------------------------------------
# LangGraph Platform API compatibility (for agent-chat-ui)
# ---------------------------------------------------------------------------


class PlatformInfoResponse(BaseModel):
    """GET /info - server info (LangGraph Platform)."""

    version: str = Field(default="1.0.0", description="API version")
    langgraph_py_version: str = Field(
        default="", description="LangGraph Python version"
    )
    flags: Dict[str, Any] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class PlatformThreadCreateRequest(BaseModel):
    """POST /threads - create thread (Platform)."""

    thread_id: Optional[str] = Field(None, description="Optional UUID for thread")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    if_exists: Optional[str] = Field("raise", description="raise | do_nothing")


class PlatformThreadResponse(BaseModel):
    """Thread object (Platform API)."""

    thread_id: str
    created_at: str = Field(..., description="ISO datetime")
    updated_at: str = Field(..., description="ISO datetime")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    status: str = Field(default="idle", description="idle | busy | interrupted | error")
    config: Dict[str, Any] = Field(default_factory=dict)
    values: Dict[str, Any] = Field(default_factory=dict)
    interrupts: Dict[str, Any] = Field(default_factory=dict)


class PlatformThreadSearchRequest(BaseModel):
    """POST /threads/search - search threads (Platform)."""

    ids: Optional[List[str]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    values: Dict[str, Any] = Field(default_factory=dict)
    status: Optional[str] = None
    limit: int = Field(default=10, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    sort_by: Optional[str] = Field(
        "updated_at", description="thread_id | status | created_at | updated_at"
    )
    sort_order: Optional[str] = Field("desc", description="asc | desc")


class PlatformRunCreateRequest(BaseModel):
    """POST /threads/{id}/runs/stream or /runs/wait (Platform)."""

    assistant_id: Optional[str] = Field(
        None, description="Graph/assistant ID (e.g. real-estate-agent)"
    )
    input: Dict[str, Any] = Field(
        default_factory=dict, description="Input state, e.g. { messages: [...] }"
    )
    stream_mode: Optional[List[str]] = Field(default=["messages"])
    config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    metadata: Optional[Dict[str, Any]] = None


class PlatformThreadHistoryRequest(BaseModel):
    """POST /threads/{thread_id}/history - get thread state history (LangGraph Platform)."""

    limit: int = Field(
        default=10, ge=1, le=1000, description="Max number of states to return"
    )
    before: Optional[Dict[str, Any]] = Field(
        None, description="Return states before this checkpoint"
    )
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    checkpoint: Optional[Dict[str, Any]] = Field(
        None, description="Filter by checkpoint"
    )


class PlatformThreadStateUpdateRequest(BaseModel):
    """POST /threads/{thread_id}/state - update thread state (LangGraph Platform)."""

    values: Optional[Dict[str, Any]] = Field(
        default_factory=dict,
        description="Partial state to merge (e.g. { files: {...} })",
    )
    checkpoint: Optional[Dict[str, Any]] = Field(
        None, description="Checkpoint to update (optional)"
    )
    as_node: Optional[str] = Field(None, description="Update as if this node executed")


class PlatformAssistantResponse(BaseModel):
    """GET /assistants/{id} - assistant object (LangGraph Platform)."""

    assistant_id: str
    graph_id: str
    config: Dict[str, Any] = Field(default_factory=dict)
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    context: Dict[str, Any] = Field(default_factory=dict)
    version: int = Field(default=1)
    name: Optional[str] = None
    description: Optional[str] = None


class PlatformAssistantsSearchRequest(BaseModel):
    """POST /assistants/search - search assistants (LangGraph Platform)."""

    metadata: Dict[str, Any] = Field(default_factory=dict)
    limit: int = Field(default=10, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    graph_id: Optional[str] = Field(None, description="Filter by graph ID")


# Auth (Phase 2)
class TokenResponse(BaseModel):
    """JWT token response."""

    access_token: str = Field(..., description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_at: datetime = Field(..., description="Expiration timestamp")


class UserCreate(BaseModel):
    """User registration request."""

    email: EmailStr = Field(..., description="User email")
    password: SecretStr = Field(
        ..., min_length=8, max_length=64, description="Password"
    )

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        p = v.get_secret_value()
        if len(p) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not re.search(r"[A-Z]", p):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", p):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", p):
            raise ValueError("Password must contain at least one number")
        return v


class UserResponse(BaseModel):
    """User response (e.g. after register)."""

    id: int = Field(..., description="User ID")
    email: str = Field(..., description="User email")
    token: TokenResponse = Field(..., description="JWT token")


class SessionResponse(BaseModel):
    """Chat session response."""

    session_id: str = Field(..., description="Session (thread) ID")
    name: str = Field(default="", max_length=100, description="Session name")
    token: TokenResponse = Field(..., description="JWT for this session")
