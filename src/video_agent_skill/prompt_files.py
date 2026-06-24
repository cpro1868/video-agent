from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib import resources
from pathlib import Path
from typing import Any

from video_agent_skill.errors import InvalidArgumentError

DEFAULT_PROMPT_FILES = (
    "default-system.txt",
    "default-video-summary.txt",
    "default-danmaku.txt",
)


@dataclass(frozen=True)
class PromptFileCopy:
    name: str
    path: str
    copied: bool


def get_prompt_info() -> dict[str, Any]:
    prompt_dir = resources.files("video_agent_skill").joinpath("prompts")
    files = []
    for name in DEFAULT_PROMPT_FILES:
        prompt_file = prompt_dir.joinpath(name)
        files.append(
            {
                "name": name,
                "package_path": str(prompt_file),
                "bytes": len(prompt_file.read_bytes()),
            }
        )
    return {
        "status": "success",
        "prompt_dir": str(prompt_dir),
        "files": files,
        "editable_copy_command": "video-agent --init-prompts prompts",
    }


def copy_default_prompts(target_dir: str | Path, *, overwrite: bool = False) -> dict[str, Any]:
    destination = Path(target_dir)
    prompt_dir = resources.files("video_agent_skill").joinpath("prompts")
    try:
        destination.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise InvalidArgumentError(f"Unable to create prompt directory: {destination}") from exc

    copied: list[PromptFileCopy] = []
    for name in DEFAULT_PROMPT_FILES:
        target = destination / name
        if target.exists() and not overwrite:
            copied.append(PromptFileCopy(name=name, path=str(target), copied=False))
            continue
        try:
            text = prompt_dir.joinpath(name).read_text(encoding="utf-8")
            target.write_text(text, encoding="utf-8")
        except OSError as exc:
            raise InvalidArgumentError(f"Unable to write prompt file: {target}") from exc
        copied.append(PromptFileCopy(name=name, path=str(target), copied=True))

    return {
        "status": "success",
        "target_dir": str(destination),
        "files": [asdict(item) for item in copied],
    }
