#!/usr/bin/env python3
"""Run the FastAPI backend.

From project root:
  cd backend && . venv/bin/activate && python run.py
  # or with PYTHONPATH from repo root:
  python backend/run.py  (requires: pip install -r backend/requirements.txt)
"""

import logging
import os
import sys
import warnings
from pathlib import Path

# Suppress Pydantic UserWarnings from deps (LangChain/DeepAgents) using typing.NotRequired
warnings.filterwarnings(
    "ignore",
    message=".*NotRequired.*",
    category=UserWarning,
    module="pydantic",
)

_backend = Path(__file__).resolve().parent
_root = _backend.parent

# So imports like "api.main", "config.settings" resolve from backend
for _p in (_root, _backend):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))
os.environ["PYTHONPATH"] = os.pathsep.join(
    [str(_root), str(_backend), os.environ.get("PYTHONPATH", "")]
)

import uvicorn  # noqa: E402
from config.settings import settings  # noqa: E402
from utils.logging_config import setup_logging  # noqa: E402

setup_logging()

# Reduce watchfiles log noise (reload still works; we just don't log every change)
logging.getLogger("watchfiles.main").setLevel(logging.WARNING)

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
        reload_dirs=[str(_backend)],
        reload_excludes=[
            "working/*",
            "memories/*",
            "reports/*",
            "logs/*",
            ".git/*",
            "*.pyc",
            "__pycache__",
        ],
    )
