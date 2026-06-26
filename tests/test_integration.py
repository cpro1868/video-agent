"""End-to-end integration tests using real video URLs.

These tests verify the complete pipeline from URL to output.
They require network access and may be slow; run with:
    uv run pytest tests/test_integration.py -v --timeout=300
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

# Pre-verified test URLs (short, stable, public videos)
YOUTUBE_SUBTITLE_URL = "https://www.youtube.com/watch?v=KGUXXUCV6S4"  # Has English subtitles
YOUTUBE_ASR_URL = "https://www.youtube.com/watch?v=eV6gHhliroA"  # Short video, likely no subtitles

# Proxy from environment or config
PROXY = os.environ.get("VIDEO_AGENT_PROXY", "http://127.0.0.1:8964")


def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Run CLI with given args, returning completed process."""
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "video_agent_skill", *args]
    return subprocess.run(
        command,
        check=False,
        capture_output=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )


def _check_asr_available() -> bool:
    """Check if ASR (SenseVoice/FunASR) is available."""
    import importlib.util
    return importlib.util.find_spec("funasr") is not None


# Skip ASR tests if FunASR is not available
_ASR_SKIPIF = pytest.mark.skipif(
    not os.environ.get("SENSEVOICE_SOURCE_DIR") and not _check_asr_available(),
    reason="ASR (FunASR/SenseVoice) not available in this environment",
)


@_ASR_SKIPIF
@pytest.mark.slow
@pytest.mark.integration
def test_youtube_asr_fallback() -> None:
    """AT-002: ASR fallback for a YouTube video without subtitles."""
    result = _run_cli(
        "-u", YOUTUBE_ASR_URL,
        "--lang", "en",
        "--proxy", PROXY,
        "--transcript-only",
        "--output-format", "json",
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["meta"]["strategy_used"] in {"subtitle", "asr"}
    assert payload["content"]["transcript_excerpt"]


@pytest.mark.slow
@pytest.mark.integration
def test_youtube_subtitle_extraction() -> None:
    """AT-001: Extract subtitles from a YouTube video with known subtitles."""
    result = _run_cli(
        "-u", YOUTUBE_SUBTITLE_URL,
        "--lang", "en",
        "--proxy", PROXY,
        "--transcript-only",
        "--output-format", "json",
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["meta"]["strategy_used"] == "subtitle"
    assert payload["content"]["transcript_excerpt"]
    assert len(payload["content"]["transcript_excerpt"]) > 100


@pytest.mark.slow
@pytest.mark.integration
def test_stdout_json_contract() -> None:
    """AT-003: stdout contains only valid JSON, no extra text."""
    result = _run_cli(
        "-u", YOUTUBE_SUBTITLE_URL,
        "--lang", "en",
        "--proxy", PROXY,
        "--transcript-only",
        "--output-format", "json",
    )

    assert result.returncode == 0
    # stdout must be parseable JSON with no extra lines
    lines = result.stdout.strip().split("\n")
    assert len(lines) == 1, "stdout should contain exactly one JSON line"
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"


@pytest.mark.slow
@pytest.mark.integration
def test_stderr_isolation() -> None:
    """AT-004: stderr contains logs, stdout contains only JSON."""
    result = _run_cli(
        "-u", YOUTUBE_SUBTITLE_URL,
        "--lang", "en",
        "--proxy", PROXY,
        "--transcript-only",
        "--output-format", "json",
    )

    assert result.returncode == 0
    # stderr may contain logs (yt-dlp, etc.), but stdout must be clean JSON
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    # stderr should not be empty (there should be some progress/info logs)
    assert result.stderr, "Expected some stderr output from yt-dlp/logs"


@pytest.mark.slow
@pytest.mark.integration
def test_markdown_output_format() -> None:
    """AT-013: Markdown output format produces valid Markdown."""
    result = _run_cli(
        "-u", YOUTUBE_SUBTITLE_URL,
        "--lang", "en",
        "--proxy", PROXY,
        "--transcript-only",
        "--output-format", "markdown",
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    # stdout should be Markdown, not JSON
    assert result.stdout.startswith("# "), "Markdown output should start with a heading"
    assert "## " in result.stdout, "Markdown should contain section headers"


@pytest.mark.slow
@pytest.mark.integration
def test_output_file_writes_json() -> None:
    """AT-014: --output-file writes valid JSON to file."""
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        output_path = f.name

    try:
        result = _run_cli(
            "-u", YOUTUBE_SUBTITLE_URL,
            "--lang", "en",
            "--proxy", PROXY,
            "--transcript-only",
            "--output-file", output_path,
            "--output-format", "json",
        )

        assert result.returncode == 0, f"CLI failed: {result.stderr}"
        # stdout should be empty when --output-file is used
        assert not result.stdout.strip(), "stdout should be empty when --output-file is used"

        # File should contain valid JSON
        content = Path(output_path).read_text(encoding="utf-8")
        payload = json.loads(content)
        assert payload["status"] == "success"
    finally:
        Path(output_path).unlink(missing_ok=True)


@pytest.mark.slow
@pytest.mark.integration
@pytest.mark.skipif(
    not os.environ.get("VIDEO_AGENT_LLM_API_KEY"),
    reason="Requires LLM API key for full summarization",
)
def test_full_llm_summarization() -> None:
    """AT-002 (full): Complete pipeline with LLM summarization."""
    result = _run_cli(
        "-u", YOUTUBE_SUBTITLE_URL,
        "--lang", "zh",
        "--proxy", PROXY,
    )

    assert result.returncode == 0, f"CLI failed: {result.stderr}"
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    content = payload["content"]
    assert content["title"]
    assert content["summary"]
    assert len(content["key_points"]) >= 3
    assert len(content["tags"]) >= 1