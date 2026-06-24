from __future__ import annotations

from pathlib import Path


def test_root_and_package_default_prompts_match() -> None:
    root = Path(__file__).resolve().parents[1]
    for name in ("default-system.txt", "default-video-summary.txt"):
        root_prompt = root / "prompts" / name
        package_prompt = root / "src" / "video_agent_skill" / "prompts" / name
        assert root_prompt.read_text(encoding="utf-8") == package_prompt.read_text(
            encoding="utf-8"
        )
