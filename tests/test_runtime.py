from __future__ import annotations

from video_agent_skill.runtime import create_runtime_context


def test_runtime_context_cleans_temp_dir(tmp_path) -> None:
    context = create_runtime_context(temp_dir=str(tmp_path), keep_temp=False)
    marker = context.work_dir / "marker.txt"
    marker.write_text("data", encoding="utf-8")

    context.cleanup()

    assert not context.work_dir.exists()


def test_runtime_context_keeps_temp_dir_when_requested(tmp_path) -> None:
    context = create_runtime_context(temp_dir=str(tmp_path), keep_temp=True)

    context.cleanup()

    assert context.work_dir.exists()
