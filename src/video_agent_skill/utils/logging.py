"""Logging utilities for Video-Agent-Skill.

Provides structured logging with severity levels, all output goes to stderr
to preserve stdout JSON contract.
"""

from __future__ import annotations

import sys
from enum import IntEnum


class LogLevel(IntEnum):
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


# Global log level, default is INFO
# Can be overridden via environment variable VIDEO_AGENT_LOG_LEVEL
_current_level = LogLevel.INFO


def set_level(level: LogLevel | str | int) -> None:
    """Set the global log level."""
    global _current_level
    if isinstance(level, LogLevel):
        _current_level = level
    elif isinstance(level, str):
        _current_level = LogLevel[level.upper()]
    else:
        _current_level = LogLevel(level)


def get_level() -> LogLevel:
    """Get the current global log level."""
    return _current_level


def _should_log(level: LogLevel) -> bool:
    return level >= _current_level


def _format_message(level: LogLevel, message: str) -> str:
    """Format a log message with level prefix."""
    return f"[{level.name}] {message}"


def debug(message: str) -> None:
    """Log a debug message (detailed internal state)."""
    if _should_log(LogLevel.DEBUG):
        print(_format_message(LogLevel.DEBUG, message), file=sys.stderr)


def info(message: str) -> None:
    """Log an info message (key workflow milestones)."""
    if _should_log(LogLevel.INFO):
        print(_format_message(LogLevel.INFO, message), file=sys.stderr)


def warning(message: str) -> None:
    """Log a warning message (degradation or recoverable issues)."""
    if _should_log(LogLevel.WARNING):
        print(_format_message(LogLevel.WARNING, message), file=sys.stderr)


def error(message: str) -> None:
    """Log an error message (failures that affect output)."""
    if _should_log(LogLevel.ERROR):
        print(_format_message(LogLevel.ERROR, message), file=sys.stderr)


def success(message: str) -> None:
    """Log a success message (final positive confirmation).

    Uses INFO level so it shows by default, but with a [SUCCESS] prefix
    for clear visual distinction from regular info logs.
    """
    if _should_log(LogLevel.INFO):
        print(f"[SUCCESS] {message}", file=sys.stderr)


def critical(message: str) -> None:
    """Log a critical message (system-level failures)."""
    if _should_log(LogLevel.CRITICAL):
        print(_format_message(LogLevel.CRITICAL, message), file=sys.stderr)


def _init_level_from_env() -> None:
    """Initialize log level from environment variable."""
    import os

    env_level = os.environ.get("VIDEO_AGENT_LOG_LEVEL", "").upper()
    if env_level:
        try:
            set_level(env_level)
        except (KeyError, ValueError):
            pass


# Auto-initialize on module import
_init_level_from_env()
