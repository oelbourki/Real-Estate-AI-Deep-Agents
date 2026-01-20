"""Backup script for reports and memories."""
import os
import tarfile
import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def create_backup(backup_dir: str = "backups") -> str:
    """
    Create backup of reports and memories.
    
    Args:
        backup_dir: Directory to store backups
        
    Returns:
        Path to backup file
    """
    # Create backup directory
    os.makedirs(backup_dir, exist_ok=True)
    
    # Generate backup filename
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"backup_{timestamp}.tar.gz"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    # Create tar archive
    with tarfile.open(backup_path, "w:gz") as tar:
        # Add reports directory
        reports_dir = Path("reports")
        if reports_dir.exists():
            tar.add(reports_dir, arcname="reports")
            logger.info(f"Added reports directory to backup")
        
        # Add memories directory
        memories_dir = Path("memories")
        if memories_dir.exists():
            tar.add(memories_dir, arcname="memories")
            logger.info(f"Added memories directory to backup")
    
    logger.info(f"Backup created: {backup_path}")
    return backup_path


def restore_backup(backup_path: str, extract_to: str = "."):
    """
    Restore from backup.
    
    Args:
        backup_path: Path to backup file
        extract_to: Directory to extract to
    """
    if not os.path.exists(backup_path):
        raise FileNotFoundError(f"Backup file not found: {backup_path}")
    
    with tarfile.open(backup_path, "r:gz") as tar:
        tar.extractall(extract_to)
        logger.info(f"Restored backup from {backup_path}")


if __name__ == "__main__":
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) < 3:
            print("Usage: python backup.py restore <backup_file>")
            sys.exit(1)
        restore_backup(sys.argv[2])
    else:
        backup_path = create_backup()
        print(f"Backup created: {backup_path}")
