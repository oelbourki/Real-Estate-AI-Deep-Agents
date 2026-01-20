"""Long-term memory system for persistent storage."""
import os
import logging
from typing import List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


def initialize_memory_files():
    """
    Initialize memory files for long-term storage.
    Creates memory directory and default memory files if they don't exist.
    """
    memory_dir = os.path.join(os.getcwd(), "memories")
    os.makedirs(memory_dir, exist_ok=True)
    
    memory_files = {
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
    
    for filename, content in memory_files.items():
        filepath = os.path.join(memory_dir, filename)
        if not os.path.exists(filepath):
            with open(filepath, "w") as f:
                f.write(content)
            logger.info(f"Created memory file: {filepath}")
    
    return memory_dir


def get_memory_paths() -> List[str]:
    """
    Get list of memory file paths for DeepAgents memory system.
    
    Returns:
        List of memory file paths
    """
    memory_dir = initialize_memory_files()
    
    memory_paths = [
        f"/memories/user_preferences.md",
        f"/memories/property_history.md",
        f"/memories/market_knowledge.md",
    ]
    
    logger.info(f"Memory system initialized with {len(memory_paths)} memory files")
    return memory_paths
