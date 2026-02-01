"""Retry logic and error recovery."""

import time
import logging
from typing import Callable, TypeVar, Optional, List
from functools import wraps

logger = logging.getLogger(__name__)

T = TypeVar("T")


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable] = None,
):
    """
    Decorator for retrying functions with exponential backoff.

    Args:
        max_attempts: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for delay after each retry
        max_delay: Maximum delay between retries
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Optional callback function called on each retry
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e

                    if attempt == max_attempts:
                        logger.error(
                            f"{func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise

                    if on_retry:
                        on_retry(attempt, e, delay)

                    logger.warning(
                        f"{func.__name__} attempt {attempt}/{max_attempts} failed: {e}. "
                        f"Retrying in {delay}s..."
                    )

                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)

            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            raise RuntimeError(f"{func.__name__} failed unexpectedly")

        return wrapper

    return decorator


def retry_on_http_error(
    max_attempts: int = 3, status_codes: Optional[List[int]] = None
):
    """
    Decorator for retrying HTTP requests on specific status codes.

    Args:
        max_attempts: Maximum number of retry attempts
        status_codes: List of HTTP status codes to retry on (default: 5xx errors)
    """
    if status_codes is None:
        status_codes = [500, 502, 503, 504, 429]  # Server errors and rate limiting

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import requests

            for attempt in range(1, max_attempts + 1):
                try:
                    response = func(*args, **kwargs)

                    # Check if response is a requests.Response object
                    if hasattr(response, "status_code"):
                        if response.status_code in status_codes:
                            if attempt < max_attempts:
                                delay = 2**attempt  # Exponential backoff
                                logger.warning(
                                    f"HTTP {response.status_code} error on attempt {attempt}. "
                                    f"Retrying in {delay}s..."
                                )
                                time.sleep(delay)
                                continue
                            else:
                                response.raise_for_status()

                    return response
                except requests.exceptions.RequestException as e:
                    if attempt < max_attempts:
                        delay = 2**attempt
                        logger.warning(
                            f"Request error on attempt {attempt}: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        time.sleep(delay)
                        continue
                    else:
                        raise

            raise RuntimeError(f"{func.__name__} failed after {max_attempts} attempts")

        return wrapper

    return decorator
