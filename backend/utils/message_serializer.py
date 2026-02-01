"""Utility functions for serializing LangChain messages to JSON format compatible with agent-chat-ui."""

from langchain_core.messages import (
    BaseMessage,
    HumanMessage,
    AIMessage,
    ToolMessage,
    SystemMessage,
)
from typing import List, Dict, Any
import json


def serialize_message(message: BaseMessage) -> Dict[str, Any]:
    """
    Serialize a LangChain message to JSON format compatible with agent-chat-ui.

    Args:
        message: LangChain message object

    Returns:
        Dictionary with message data in LangGraph format
    """
    # Base message structure
    msg_dict = {
        "type": message.__class__.__name__.lower().replace("message", ""),
        "content": message.content if hasattr(message, "content") else str(message),
    }

    # Add role for different message types
    if isinstance(message, HumanMessage):
        msg_dict["role"] = "user"
    elif isinstance(message, AIMessage):
        msg_dict["role"] = "assistant"
    elif isinstance(message, SystemMessage):
        msg_dict["role"] = "system"
    elif isinstance(message, ToolMessage):
        msg_dict["role"] = "tool"
        # Tool messages have tool_call_id
        if hasattr(message, "tool_call_id"):
            msg_dict["tool_call_id"] = message.tool_call_id
        if hasattr(message, "name"):
            msg_dict["name"] = message.name

    # Add tool calls if present (for AIMessage)
    if (
        isinstance(message, AIMessage)
        and hasattr(message, "tool_calls")
        and message.tool_calls
    ):
        msg_dict["tool_calls"] = []
        for tool_call in message.tool_calls:
            tool_call_dict = {
                "id": tool_call.get("id", ""),
                "type": "function",
                "function": {
                    "name": tool_call.get("name", ""),
                    "arguments": json.dumps(tool_call.get("args", {}))
                    if isinstance(tool_call.get("args"), dict)
                    else str(tool_call.get("args", "")),
                },
            }
            msg_dict["tool_calls"].append(tool_call_dict)

    # Add additional metadata if present
    if hasattr(message, "additional_kwargs") and message.additional_kwargs:
        msg_dict["additional_kwargs"] = message.additional_kwargs

    # Add ID if present
    if hasattr(message, "id"):
        msg_dict["id"] = message.id

    return msg_dict


def serialize_messages(messages: List[BaseMessage]) -> List[Dict[str, Any]]:
    """
    Serialize a list of LangChain messages to JSON format.

    Args:
        messages: List of LangChain message objects

    Returns:
        List of serialized message dictionaries
    """
    return [serialize_message(msg) for msg in messages]
