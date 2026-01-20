"""API request/response schemas for OpenAPI documentation."""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import time


class ChatRequest(BaseModel):
    """Chat request schema."""
    message: str = Field(..., description="User message to the agent")
    conversation_id: Optional[str] = Field(None, description="Conversation ID for context (optional)")
    user_name: Optional[str] = Field(None, description="User name for personalization (optional)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Find 3 bedroom houses in San Francisco under $2M",
                "user_name": "John"
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
                "timestamp": 1706359845.123
            }
        }


class LangGraphChatResponse(BaseModel):
    """LangGraph-compatible chat response schema for agent-chat-ui."""
    messages: List[Dict[str, Any]] = Field(..., description="List of messages in LangGraph format")
    thread_id: str = Field(..., description="Thread/conversation ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "messages": [
                    {
                        "type": "human",
                        "role": "user",
                        "content": "Find houses in San Francisco"
                    },
                    {
                        "type": "ai",
                        "role": "assistant",
                        "content": "I found several properties..."
                    }
                ],
                "thread_id": "thread_1234567890"
            }
        }


class PropertySearchRequest(BaseModel):
    """Property search request schema."""
    location: str = Field(..., description="Location to search (e.g., 'San Francisco, CA')")
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
                "bathrooms": 2
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
                        "baths": 2
                    }
                ],
                "total": 1
            }
        }


class HealthResponse(BaseModel):
    """Health check response schema."""
    status: str = Field(..., description="Health status")
    version: str = Field(..., description="Application version")
    redis: str = Field(..., description="Redis connection status")
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


# LangGraph Platform API Compatibility Schemas
class ThreadCreateRequest(BaseModel):
    """Request to create a new thread."""
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Optional thread metadata")


class ThreadResponse(BaseModel):
    """Thread response schema."""
    thread_id: str = Field(..., description="Thread ID")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Thread metadata")
    created_at: Optional[float] = Field(default_factory=time.time, description="Creation timestamp")


class RunCreateRequest(BaseModel):
    """Request to create a run."""
    input: Dict[str, Any] = Field(..., description="Input for the run, typically contains 'messages'")
    stream_mode: Optional[str] = Field("updates", description="Streaming mode: 'updates', 'values', or 'messages'")
    config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Run configuration")


class RunResponse(BaseModel):
    """Run response schema."""
    run_id: str = Field(..., description="Run ID")
    thread_id: str = Field(..., description="Thread ID")
    assistant_id: str = Field(..., description="Assistant ID")
    status: str = Field(..., description="Run status: 'pending', 'running', 'completed', 'failed'")
    input: Dict[str, Any] = Field(..., description="Run input")
    output: Optional[Dict[str, Any]] = Field(None, description="Run output")
    error: Optional[str] = Field(None, description="Error message if failed")
    created_at: float = Field(default_factory=time.time, description="Creation timestamp")
    completed_at: Optional[float] = Field(None, description="Completion timestamp")
