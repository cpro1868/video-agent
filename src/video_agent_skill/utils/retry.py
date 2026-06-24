"""Retry utilities with exponential backoff and max attempts.

Provides configurable retry logic for network and transient failures.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from video_agent_skill.errors import NetworkError
from video_agent_skill.utils.logging import info, warning

T = TypeVar("T")

DEFAULT_MAX_RETRIES = 3
DEFAULT_BASE_DELAY = 2.0  # seconds


def with_retry(
    operation: Callable[[], T],
    *,
    max_retries: int = DEFAULT_MAX_RETRIES,
    base_delay: float = DEFAULT_BASE_DELAY,
    retryable_exceptions: tuple[type[Exception], ...] = (
        NetworkError, ConnectionError, TimeoutError
    ),
    operation_name: str = "operation",
) -> T:
    """Execute an operation with retry logic.

    Retries on specified exceptions with exponential backoff.
    After max_retries failures, raises the last exception.

    Args:
        operation: Callable to execute.
        max_retries: Maximum number of retry attempts (default 3).
        base_delay: Base delay in seconds between retries (default 2.0).
        retryable_exceptions: Tuple of exception types to retry on.
        operation_name: Human-readable name for logging.

    Returns:
        Result of the operation.

    Raises:
        The last exception if all retries are exhausted.
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            if attempt > 0:
                info(f"Retrying {operation_name} (attempt {attempt + 1}/{max_retries + 1})")
            return operation()
        except retryable_exceptions as exc:
            last_exception = exc
            if attempt < max_retries:
                delay = base_delay * (2 ** attempt)  # Exponential backoff: 2, 4, 8, ...
                warning(
                    f"{operation_name} failed (attempt {attempt + 1}/{max_retries + 1}): "
                    f"{exc}. Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
            else:
                warning(
                    f"{operation_name} failed after {max_retries + 1} attempts. "
                    f"Last error: {exc}"
                )

    # All retries exhausted
    if last_exception is not None:
        raise last_exception
    raise RuntimeError(f"Unexpected state in retry logic for {operation_name}")
