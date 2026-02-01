"""Long-term memory system for persistent storage."""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import List

from backend.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

# When called from ASGI (event loop running), run blocking I/O in this pool to avoid BlockingError
_io_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="backend_io")

_MEMORY_FILES = {
    "user_preferences.md": """# User Preferences

This file stores user preferences and search history.

## Search Preferences
- Default location: None
- Property types: None
- Price range: None
- Bedrooms: None
- Bathrooms: None

## Preferences History
""",
    "property_history.md": """# Property History

This file tracks previously viewed and analyzed properties.

## Properties Analyzed
""",
    "market_knowledge.md": """# Market Knowledge

This file stores learned market insights and trends.

## Market Insights
""",
}


def _do_initialize_memory_files() -> str:
    """Create memory dir and default files (sync; run via thread or async to avoid blocking event loop)."""
    memory_dir = str(PROJECT_ROOT / "memories")
    os.makedirs(memory_dir, exist_ok=True)
    for filename, content in _MEMORY_FILES.items():
        filepath = os.path.join(memory_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write(content)
            logger.info("Created memory file: %s", filepath)
    return memory_dir


def _run_off_loop(fn, *args, **kwargs):
    """Run blocking fn off the event loop: in thread if loop is running, else directly."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn(*args, **kwargs)
    return _io_executor.submit(fn, *args, **kwargs).result()


async def initialize_memory_files_async() -> str:
    """
    Async: initialize memory files. Use when the caller can await (e.g. async graph factory).
    Uses asyncio.to_thread so the event loop is not blocked.
    """
    return await asyncio.to_thread(_do_initialize_memory_files)


def initialize_memory_files() -> str:
    """
    Initialize memory files for long-term storage (sync).
    When called from LangGraph ASGI, runs in a thread to avoid BlockingError.
    """
    return _run_off_loop(_do_initialize_memory_files)


def get_memory_paths() -> List[str]:
    """
    Get list of memory file paths for DeepAgents memory system.

    Returns:
        List of memory file paths
    """
    initialize_memory_files()
    memory_paths = [
        "/memories/user_preferences.md",
        "/memories/property_history.md",
        "/memories/market_knowledge.md",
    ]

    logger.info(f"Memory system initialized with {len(memory_paths)} memory files")
    return memory_paths
