"""Token counting utilities for request validation."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# System prompt overhead (estimated from MAIN_AGENT_SYSTEM_PROMPT)
# Based on actual API errors: "Find houses in San Francisco" (~15 tokens) resulted in 8356 total tokens
# This means overhead is ~8341 tokens. Breaking it down:
SYSTEM_PROMPT_OVERHEAD = 1120  # System prompt tokens (~4473 chars / 4)
TOOL_DESCRIPTIONS_OVERHEAD = (
    2000  # Tool descriptions and schemas (2 tools + DeepAgents tools)
)
SUBAGENT_OVERHEAD = (
    2500  # Subagent descriptions and prompts (6 subagents with full descriptions)
)
MEMORY_OVERHEAD = 300  # Memory context (if conversation exists)
FILESYSTEM_OVERHEAD = 1000  # Filesystem context and file listings
DEEPAGENTS_MIDDLEWARE_OVERHEAD = (
    2500  # DeepAgents middleware overhead (todos, planning, task tool, etc.)
)
TOTAL_BASE_OVERHEAD = (
    SYSTEM_PROMPT_OVERHEAD
    + TOOL_DESCRIPTIONS_OVERHEAD
    + SUBAGENT_OVERHEAD
    + FILESYSTEM_OVERHEAD
    + DEEPAGENTS_MIDDLEWARE_OVERHEAD
)  # ~9120 tokens base overhead (conservative estimate)


def estimate_tokens(text: str, model: Optional[str] = None) -> int:
    """
    Estimate token count for a text string.

    Uses a simple approximation: ~4 characters per token (average for English).
    This is a conservative estimate that works well for most cases.

    Args:
        text: Input text to count tokens for
        model: Optional model name (for future model-specific counting)

    Returns:
        Estimated token count
    """
    if not text:
        return 0

    # Simple approximation: ~4 characters per token
    # This is conservative and works well for English text
    # For more accuracy, could use tiktoken, but this avoids extra dependencies
    char_count = len(text)
    estimated_tokens = char_count // 4

    return estimated_tokens


def estimate_message_tokens(
    message: str,
    user_name: Optional[str] = None,
    conversation_id: Optional[str] = None,
    include_overhead: bool = True,
) -> int:
    """
    Estimate total tokens for a chat message including all overhead.

    This includes:
    - User message
    - System prompt (~2500 tokens)
    - DeepAgents middleware overhead (~2000 tokens)
    - Tool descriptions (~500 tokens)
    - Subagent descriptions (~800 tokens)
    - Memory context (~200 tokens if conversation exists)
    - Filesystem context (~300 tokens)

    Args:
        message: User message content
        user_name: Optional user name (adds to token count)
        conversation_id: Optional conversation ID (adds memory overhead)
        include_overhead: Whether to include system/middleware overhead

    Returns:
        Estimated total token count
    """
    # Estimate user message tokens
    total_text = message

    # Add user name if provided (as it's prepended to message)
    if user_name:
        total_text = f"[User Name: {user_name}]\n\n{message}"

    user_message_tokens = estimate_tokens(total_text)

    if not include_overhead:
        return user_message_tokens

    # Add all overhead components
    total_tokens = user_message_tokens

    # Base overhead (always present)
    total_tokens += SYSTEM_PROMPT_OVERHEAD
    total_tokens += TOOL_DESCRIPTIONS_OVERHEAD
    total_tokens += SUBAGENT_OVERHEAD
    total_tokens += FILESYSTEM_OVERHEAD
    total_tokens += DEEPAGENTS_MIDDLEWARE_OVERHEAD

    # Conditional overhead
    if conversation_id:
        total_tokens += MEMORY_OVERHEAD

    return total_tokens


def validate_token_limit(
    message: str,
    max_tokens: int,
    user_name: Optional[str] = None,
    conversation_id: Optional[str] = None,
) -> tuple[bool, int, Optional[str]]:
    """
    Validate if a message exceeds token limit.

    This estimates the FULL request size including:
    - User message
    - System prompt
    - DeepAgents middleware overhead
    - Tool/subagent descriptions
    - Memory context (if conversation exists)

    Args:
        message: User message content
        max_tokens: Maximum allowed tokens
        user_name: Optional user name
        conversation_id: Optional conversation ID (adds memory overhead)

    Returns:
        Tuple of (is_valid, estimated_tokens, error_message)
    """
    # Estimate full request including all overhead
    estimated = estimate_message_tokens(
        message, user_name, conversation_id, include_overhead=True
    )

    if estimated > max_tokens:
        # Calculate how much to reduce from user message
        user_message_tokens = estimate_message_tokens(
            message, user_name, include_overhead=False
        )
        overhead = estimated - user_message_tokens
        max_user_tokens = max_tokens - overhead

        error_msg = (
            f"Request too large: estimated {estimated} tokens (user message: ~{user_message_tokens}, "
            f"system overhead: ~{overhead}) exceeds limit of {max_tokens} tokens. "
            f"Please reduce your message size by approximately {estimated - max_tokens} tokens "
            f"({int((estimated - max_tokens) / estimated * 100)}% reduction needed). "
            f"Maximum user message size: ~{max_user_tokens} tokens."
        )
        return False, estimated, error_msg

    return True, estimated, None
