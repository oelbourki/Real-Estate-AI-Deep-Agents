"""Centralized logging configuration for console and file."""

import logging
from pathlib import Path

try:
    from config.settings import settings
except ImportError:
    from backend.config.settings import settings

# Backend directory (backend/utils -> backend)
BACKEND_DIR = Path(__file__).resolve().parent.parent

LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"


def setup_logging() -> None:
    """
    Configure root logger to log to both console (stderr) and a file.
    Log level and file path come from settings (LOG_LEVEL, LOG_FILE).
    """
    root = logging.getLogger()
    level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    root.setLevel(level)

    # Avoid adding duplicate handlers if setup_logging() is called more than once
    if root.handlers:
        return

    formatter = logging.Formatter(LOG_FORMAT)

    # Console (stderr)
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(formatter)
    root.addHandler(console)

    # File: default backend/logs/app.log unless LOG_FILE is set (use "" to disable file logging)
    log_file = getattr(settings, "log_file", None)
    if log_file is None:
        log_path = BACKEND_DIR / "logs" / "app.log"
    elif log_file == "":
        log_path = None
    else:
        log_path = Path(log_file)

    if log_path is not None:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
