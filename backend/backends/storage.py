"""Storage backend configuration.

Sync entry point: get_backend() — used by create_main_agent() (LangGraph calls it synchronously).
When an event loop is running (e.g. LangGraph ASGI), blocking I/O runs in a thread pool to avoid
BlockingError. When no loop is running (e.g. scripts), I/O runs directly.

Async entry point: get_backend_async() — use when the caller can await (e.g. if LangGraph
adds async graph factory support). Uses asyncio.to_thread() so the event loop is not blocked.
"""

import asyncio
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple

from deepagents.backends import CompositeBackend, FilesystemBackend

from backend.config.settings import PROJECT_ROOT

logger = logging.getLogger(__name__)

# When called from ASGI (event loop running), run blocking I/O in this pool to avoid BlockingError
_io_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="backend_io")


def _ensure_dirs() -> Tuple[str, str, str]:
    """Create reports, memories, working dirs (sync; run via thread or async to avoid blocking event loop)."""
    reports_dir = str(PROJECT_ROOT / "reports")
    memories_dir = str(PROJECT_ROOT / "memories")
    working_dir = str(PROJECT_ROOT / "working")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(memories_dir, exist_ok=True)
    os.makedirs(working_dir, exist_ok=True)
    return reports_dir, memories_dir, working_dir


def _run_off_loop(fn, *args, **kwargs):
    """Run blocking fn off the event loop: in thread if loop is running, else directly."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return fn(*args, **kwargs)
    return _io_executor.submit(fn, *args, **kwargs).result()


async def get_backend_async():
    """
    Async: get storage backend. Use when the caller can await (e.g. async graph factory).
    Uses asyncio.to_thread so the event loop is not blocked.
    """
    reports_dir, memories_dir, working_dir = await asyncio.to_thread(_ensure_dirs)
    return _build_backend(reports_dir, memories_dir, working_dir)


def get_backend():
    """
    Get the storage backend for the agent (sync).
    When called from LangGraph ASGI, runs makedirs in a thread to avoid BlockingError.
    """
    reports_dir, memories_dir, working_dir = _run_off_loop(_ensure_dirs)
    return _build_backend(reports_dir, memories_dir, working_dir)


def _build_backend(reports_dir: str, memories_dir: str, working_dir: str):
    """Build CompositeBackend from directory paths."""
    default_backend = FilesystemBackend(root_dir=working_dir)
    backend = CompositeBackend(
        default=default_backend,
        routes={
            "/reports/": FilesystemBackend(root_dir=reports_dir),
            "/memories/": FilesystemBackend(root_dir=memories_dir),
        },
    )
    logger.info("Using CompositeBackend with FilesystemBackend")
    logger.info("Default working directory: %s", working_dir)
    logger.info("Reports directory: %s", reports_dir)
    logger.info("Memories directory: %s", memories_dir)
    return backend
