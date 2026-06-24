from __future__ import annotations

from video_agent_skill import doctor
from video_agent_skill.utils.config import AppConfig, AsrConfig, LlmConfig


def test_run_doctor_returns_warning_when_dependencies_missing(monkeypatch) -> None:
    monkeypatch.setattr(doctor, "find_spec", lambda module_name: None)
    monkeypatch.setattr(doctor.shutil, "which", lambda name: None)
    monkeypatch.setattr(doctor, "select_asr_device", lambda device: "cpu")

    result = doctor.run_doctor(config=AppConfig(), asr=AsrConfig(), llm=LlmConfig())

    assert result["status"] == "warning"
    checks = {item["name"]: item for item in result["checks"]}
    assert checks["yt-dlp"]["ok"] is False
    assert checks["ffmpeg"]["ok"] is False
    assert checks["asr_device"]["ok"] is True


def test_sensevoice_source_dir_check(tmp_path) -> None:
    source_dir = tmp_path / "SenseVoice"
    source_dir.mkdir()
    model_file = source_dir / "model.py"
    model_file.write_text("# model", encoding="utf-8")

    check = doctor._check_sensevoice_source_dir(str(source_dir))

    assert check.ok is True
    assert check.detail == str(model_file)
