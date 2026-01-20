"""Storage backend configuration."""
from deepagents.backends import FilesystemBackend, CompositeBackend
from config.settings import settings
import logging
import os

logger = logging.getLogger(__name__)


def get_backend():
    """
    Get the storage backend for the agent.
    
    Phase 3: Enhanced backend with Filesystem and Composite support
    
    Returns:
        Backend instance
    """
    # Create directories if they don't exist
    reports_dir = os.path.join(os.getcwd(), "reports")
    memories_dir = os.path.join(os.getcwd(), "memories")
    os.makedirs(reports_dir, exist_ok=True)
    os.makedirs(memories_dir, exist_ok=True)
    
    # Phase 3: Composite backend with routing
    # Use FilesystemBackend as default instead of StateBackend (which requires runtime)
    # This provides persistent storage for all files
    default_backend = FilesystemBackend(root_dir=os.path.join(os.getcwd(), "working"))
    os.makedirs(os.path.join(os.getcwd(), "working"), exist_ok=True)
    
    backend = CompositeBackend(
        default=default_backend,  # Working files in filesystem
        routes={
            "/reports/": FilesystemBackend(root_dir=reports_dir),  # Reports on disk
            "/memories/": FilesystemBackend(root_dir=memories_dir),  # Long-term memory on disk
        }
    )
    
    logger.info(f"Using CompositeBackend with FilesystemBackend")
    logger.info(f"Default working directory: {os.path.join(os.getcwd(), 'working')}")
    logger.info(f"Reports directory: {reports_dir}")
    logger.info(f"Memories directory: {memories_dir}")
    return backend
