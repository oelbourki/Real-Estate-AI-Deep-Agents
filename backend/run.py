#!/usr/bin/env python3
"""Run script for the Real Estate AI Deep Agents backend.

Run from project root with the backend venv active so the reload worker sees the same env:
  cd backend && . venv/bin/activate && PYTHONPATH=.. python run.py
  or from repo root: backend/venv/bin/python backend/run.py
"""

import os
import sys
from pathlib import Path

# Ensure project root and backend are on path (root-based runs)
_root = Path(__file__).resolve().parent.parent
_backend = Path(__file__).resolve().parent
for _p in (_root, _backend):
    _s = str(_p)
    if _s not in sys.path:
        sys.path.insert(0, _s)

# So the uvicorn reload worker (spawned subprocess) inherits the same path
_existing = os.environ.get("PYTHONPATH", "")
_extra = os.pathsep.join([str(_root), str(_backend)])
os.environ["PYTHONPATH"] = _extra + (os.pathsep + _existing if _existing else "")

# Imports must follow sys.path setup so config/settings resolve (root-based runs)
import uvicorn  # noqa: E402
from config.settings import settings  # noqa: E402
from utils.logging_config import setup_logging  # noqa: E402

# Configure logging (console + file)
setup_logging()

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.environment == "development",
        log_level=settings.log_level.lower(),
    )
