from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from video_agent_skill.cli import _build_transcript_only_content


def run_cli(*args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(Path(__file__).resolve().parents[1] / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env.get("PYTHONPATH", "")
    command = [sys.executable, "-m", "video_agent_skill", *args]
    return subprocess.run(
        command, check=False, capture_output=True, text=True, encoding="utf-8", env=env, cwd=cwd
    )


def test_missing_url_returns_error_json_only_on_stdout() -> None:
    result = run_cli("--lang", "zh")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["content"] is None
    assert payload["error"]["code"] == "INVALID_ARGUMENT"


def test_doctor_does_not_require_url() -> None:
    result = run_cli("--doctor")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] in {"success", "warning"}
    assert isinstance(payload["checks"], list)


def test_help_is_human_readable_and_does_not_emit_json_error() -> None:
    result = run_cli("--help")

    assert result.returncode == 0
    assert result.stdout == ""
    assert "--sensevoice-source-dir" in result.stderr
    assert "--transcript-only" in result.stderr
    assert "--llm-system-prompt-file" in result.stderr
    assert "--llm-user-prompt-file" in result.stderr
    assert "--prompt-info" in result.stderr
    assert "--init-prompts" in result.stderr


def test_prompt_info_outputs_json_without_url() -> None:
    result = run_cli("--prompt-info")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert payload["files"][0]["name"] == "default-system.txt"


def test_init_prompts_copies_default_files(tmp_path) -> None:
    target_dir = tmp_path / "editable-prompts"

    result = run_cli("--init-prompts", str(target_dir))

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["status"] == "success"
    assert (target_dir / "default-system.txt").exists()
    assert (target_dir / "default-video-summary.txt").exists()


def test_invalid_url_still_preserves_json_contract() -> None:
    result = run_cli("-u", "not-a-url", "--lang", "en")

    assert result.returncode == 1
    payload = json.loads(result.stdout)
    assert payload["status"] == "error"
    assert payload["meta"]["url"] == "not-a-url"
    assert payload["meta"]["language"] == "en"
    assert payload["error"]["code"] == "UNSUPPORTED_URL"
    assert "Traceback" not in result.stdout


def test_transcript_only_content_preserves_schema_and_excerpt() -> None:
    content = _build_transcript_only_content("hello transcript")

    assert content.summary
    assert len(content.key_points) == 3
    assert content.tags == ["transcript-only"]
    assert content.transcript_excerpt == "hello transcript"
