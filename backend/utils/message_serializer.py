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
    # agent-chat-ui ToolCalls component expects each tc to have tc.args as an object (never null/undefined)
    if (
        isinstance(message, AIMessage)
        and hasattr(message, "tool_calls")
        and message.tool_calls
    ):
        msg_dict["tool_calls"] = []
        for tool_call in message.tool_calls:
            raw_args = (
                tool_call.get("args")
                if isinstance(tool_call, dict)
                else getattr(tool_call, "args", None)
            )
            args_obj = raw_args if isinstance(raw_args, dict) else {}
            if args_obj is None:
                args_obj = {}
            name = (
                tool_call.get("name", "")
                if isinstance(tool_call, dict)
                else getattr(tool_call, "name", "")
            )
            tool_call_dict = {
                "id": tool_call.get("id", "")
                if isinstance(tool_call, dict)
                else getattr(tool_call, "id", ""),
                "type": "function",
                "name": name,
                "args": args_obj,
                "function": {
                    "name": name,
                    "arguments": json.dumps(args_obj),
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
