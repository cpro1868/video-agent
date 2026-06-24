from __future__ import annotations

import shutil
from dataclasses import asdict, dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from video_agent_skill.core.transcriber import select_asr_device
from video_agent_skill.errors import VideoAgentError
from video_agent_skill.utils.config import AppConfig, AsrConfig, LlmConfig
from video_agent_skill.utils.logging import info


@dataclass(frozen=True)
class DoctorCheck:
    name: str
    ok: bool
    detail: str


def run_doctor(*, config: AppConfig, asr: AsrConfig, llm: LlmConfig) -> dict[str, Any]:
    info("Running environment diagnostics...")
    checks = [
        _check_python_dependency("yt-dlp", "yt_dlp"),
        _check_executable("ffmpeg"),
        _check_python_dependency("funasr", "funasr"),
        _check_python_dependency("torch", "torch"),
        _check_asr_device(asr.device),
        _check_sensevoice_source_dir(asr.source_dir),
        _check_llm_config(llm),
        _check_temp_dir(config.system.temp_dir),
    ]
    ok_count = sum(1 for c in checks if c.ok)
    info(f"Doctor complete: {ok_count}/{len(checks)} checks passed")
    return {
        "status": "success" if all(check.ok for check in checks) else "warning",
        "checks": [asdict(check) for check in checks],
    }


def _check_python_dependency(name: str, module_name: str) -> DoctorCheck:
    if find_spec(module_name) is None:
        return DoctorCheck(name=name, ok=False, detail=f"Python module '{module_name}' not found.")
    return DoctorCheck(name=name, ok=True, detail=f"Python module '{module_name}' is importable.")


def _check_executable(name: str) -> DoctorCheck:
    path = shutil.which(name)
    if path is None:
        return DoctorCheck(name=name, ok=False, detail=f"Executable '{name}' not found on PATH.")
    return DoctorCheck(name=name, ok=True, detail=path)


def _check_asr_device(device: str) -> DoctorCheck:
    try:
        selected = select_asr_device(device)
    except VideoAgentError as exc:
        return DoctorCheck(name="asr_device", ok=False, detail=str(exc))
    return DoctorCheck(name="asr_device", ok=True, detail=f"selected={selected}")


def _check_sensevoice_source_dir(source_dir: str) -> DoctorCheck:
    if not source_dir:
        return DoctorCheck(
            name="sensevoice_source_dir",
            ok=True,
            detail="not configured; FunASR default remote/model implementation will be used.",
        )

    path = Path(source_dir)
    model_file = path / "model.py"
    if not path.exists():
        return DoctorCheck(name="sensevoice_source_dir", ok=False, detail=f"{path} does not exist.")
    if not model_file.exists():
        return DoctorCheck(
            name="sensevoice_source_dir",
            ok=False,
            detail=f"{model_file} does not exist.",
        )
    return DoctorCheck(name="sensevoice_source_dir", ok=True, detail=str(model_file))


def _check_llm_config(llm: LlmConfig) -> DoctorCheck:
    if not llm.api_base:
        return DoctorCheck(name="llm_config", ok=False, detail="LLM api_base is empty.")
    return DoctorCheck(
        name="llm_config",
        ok=True,
        detail=f"api_base={llm.api_base}; model={llm.model_name}; timeout={llm.timeout_seconds}s",
    )


def _check_temp_dir(temp_dir: str) -> DoctorCheck:
    if not temp_dir:
        return DoctorCheck(name="temp_dir", ok=True, detail="using system temp directory.")
    path = Path(temp_dir)
    if path.exists() and path.is_dir():
        return DoctorCheck(name="temp_dir", ok=True, detail=str(path))
    return DoctorCheck(name="temp_dir", ok=False, detail=f"{path} does not exist or is not a dir.")
