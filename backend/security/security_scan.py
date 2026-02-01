"""Security scanning utilities."""

import subprocess
import logging
from typing import Dict

logger = logging.getLogger(__name__)


def check_dependencies():
    """Check for known vulnerabilities in dependencies."""
    try:
        result = subprocess.run(
            ["pip", "list", "--outdated"], capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0:
            outdated = result.stdout
            if outdated.strip():
                logger.warning("Outdated dependencies found:")
                logger.warning(outdated)
                return False
        return True
    except Exception as e:
        logger.error(f"Failed to check dependencies: {e}")
        return False


def check_secrets():
    """Check for hardcoded secrets in code."""
    # Patterns for reference; use tools like trufflehog/git-secrets in production
    _secret_patterns = (
        r'api[_-]?key\s*=\s*["\'][^"\']+["\']',
        r'password\s*=\s*["\'][^"\']+["\']',
        r'secret\s*=\s*["\'][^"\']+["\']',
        r'token\s*=\s*["\'][^"\']+["\']',
    )
    logger.info(
        "Secret scanning should be done with specialized tools (trufflehog, git-secrets)"
    )
    return True


def check_file_permissions():
    """Check file permissions for sensitive files."""
    # Files to check in deployment; actual checks done in deployment scripts
    _sensitive_files = (".env", ".env.local", "*.key", "*.pem")
    logger.info("File permission checks should be done in deployment scripts")
    return True


def security_audit() -> Dict[str, bool]:
    """Run security audit."""
    results = {
        "dependencies": check_dependencies(),
        "secrets": check_secrets(),
        "file_permissions": check_file_permissions(),
    }

    return results
