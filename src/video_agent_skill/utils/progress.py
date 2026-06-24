"""Progress reporting utilities for long-running operations.

Outputs progress events as JSON Lines to stderr, allowing Agents to
monitor processing status without interfering with stdout output.

When progress_bar is enabled, also shows a visual progress bar in the
terminal for human-friendly interactive use.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from time import time


@dataclass(frozen=True)
class ProgressEvent:
    """A progress event for Agent consumption."""

    stage: str  # e.g., "extraction", "asr", "llm_summary"
    status: str  # "started", "in_progress", "completed", "failed"
    percent: int = 0  # 0-100
    detail: str = ""  # Human-readable detail
    elapsed_seconds: float = 0.0
    extra: dict[str, object] = field(default_factory=dict)


def _emit_progress(event: ProgressEvent) -> None:
    """Emit a progress event as JSON to stderr."""
    payload = {
        "type": "progress",
        "stage": event.stage,
        "status": event.status,
        "percent": event.percent,
        "detail": event.detail,
        "elapsed_seconds": round(event.elapsed_seconds, 1),
        **event.extra,
    }
    print(json.dumps(payload, ensure_ascii=False), file=sys.stderr)


def _draw_progress_bar(stage: str, percent: int, detail: str, elapsed: float) -> None:
    """Draw a simple ASCII progress bar to stderr."""
    bar_width = 30
    filled = int(bar_width * percent / 100)
    bar = "█" * filled + "░" * (bar_width - filled)
    # Clear line and redraw
    sys.stderr.write(f"\r\033[K[{bar}] {percent:3d}% │ {stage:15s} │ {elapsed:5.1f}s │ {detail}")
    if percent >= 100:
        sys.stderr.write("\n")
    sys.stderr.flush()


class ProgressTracker:
    """Track and report progress for a multi-stage operation."""

    def __init__(self, *, progress_bar: bool = False) -> None:
        self._start_time = time()
        self._stage_start_time: float | None = None
        self._current_stage: str = ""
        self._progress_bar = progress_bar

    def _elapsed(self) -> float:
        return time() - self._start_time

    def _stage_elapsed(self) -> float:
        if self._stage_start_time is None:
            return 0.0
        return time() - self._stage_start_time

    def start_stage(self, stage: str, detail: str = "") -> None:
        """Start a new processing stage."""
        self._current_stage = stage
        self._stage_start_time = time()
        _emit_progress(
            ProgressEvent(
                stage=stage,
                status="started",
                detail=detail,
                elapsed_seconds=self._elapsed(),
            )
        )
        if self._progress_bar:
            _draw_progress_bar(stage, 0, detail, self._elapsed())

    def update(self, percent: int, detail: str = "") -> None:
        """Update progress within current stage."""
        _emit_progress(
            ProgressEvent(
                stage=self._current_stage,
                status="in_progress",
                percent=max(0, min(100, percent)),
                detail=detail,
                elapsed_seconds=self._elapsed(),
            )
        )
        if self._progress_bar:
            _draw_progress_bar(self._current_stage, percent, detail, self._elapsed())

    def complete(self, detail: str = "") -> None:
        """Mark current stage as completed."""
        _emit_progress(
            ProgressEvent(
                stage=self._current_stage,
                status="completed",
                percent=100,
                detail=detail,
                elapsed_seconds=self._elapsed(),
            )
        )
        if self._progress_bar:
            _draw_progress_bar(self._current_stage, 100, detail, self._elapsed())

    def fail(self, detail: str = "") -> None:
        """Mark current stage as failed."""
        _emit_progress(
            ProgressEvent(
                stage=self._current_stage,
                status="failed",
                detail=detail,
                elapsed_seconds=self._elapsed(),
            )
        )
        if self._progress_bar:
            sys.stderr.write(f"\r\033[K[FAILED] {self._current_stage} │ {detail}\n")
            sys.stderr.flush()
