"""Configuration initialization utilities.

The bundled `config.yaml` (shipped in the wheel, listed in RECORD so pip
uninstall removes it) serves as the default configuration. Users edit it
directly in site-packages, or override via:

1. VIDEO_AGENT_CONFIG_FILE env var pointing to a custom config
2. ./config.yaml in the current working directory

Prompt template files also stay inside the package (version-locked to the
code) and can be copied to a local directory for editing via --init-prompts.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import Any

from video_agent_skill.errors import InvalidArgumentError

DEFAULT_CONFIG_FILENAME = "config.yaml"
DEFAULT_PROMPT_FILES = (
    "default-system.txt",
    "default-video-summary.txt",
    "default-danmaku.txt",
)


def _get_package_dir() -> Path:
    """Get the package installation directory."""
    return Path(resources.files("video_agent_skill"))


def _get_package_prompt_dir() -> Path:
    """Get the package prompts directory."""
    return _get_package_dir() / "prompts"


def get_default_config_path() -> Path:
    """Get the path to the bundled config.yaml (default configuration)."""
    return _get_package_dir() / DEFAULT_CONFIG_FILENAME


def init_config(
    target_dir: str | Path | None = None,
    *,
    overwrite: bool = False,
    include_prompts: bool = True,
) -> dict[str, Any]:
    """Copy configuration files to a target directory for editing.

    Args:
        target_dir: Destination directory. If None, uses the current working
            directory.
        overwrite: Whether to overwrite existing files.
        include_prompts: Whether to also copy prompt files as templates.

    Returns:
        JSON-serializable dict with status and copied files info.
    """
    destination = Path(target_dir) if target_dir else Path.cwd()

    results: list[dict[str, Any]] = []

    config_target = destination / DEFAULT_CONFIG_FILENAME
    config_copied = _copy_config_file(config_target, overwrite=overwrite)
    results.append(
        {
            "name": DEFAULT_CONFIG_FILENAME,
            "path": str(config_target),
            "copied": config_copied,
        }
    )

    if include_prompts:
        prompt_dir = destination / "prompts"
        try:
            prompt_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise InvalidArgumentError(
                f"Unable to create prompt directory: {prompt_dir}"
            ) from exc

        package_prompt_dir = resources.files("video_agent_skill").joinpath("prompts")
        for name in DEFAULT_PROMPT_FILES:
            target = prompt_dir / name
            copied = _copy_prompt_file(package_prompt_dir, target, name, overwrite=overwrite)
            results.append(
                {
                    "name": f"prompts/{name}",
                    "path": str(target),
                    "copied": copied,
                }
            )

    return {
        "status": "success",
        "target_dir": str(destination),
        "files": results,
        "message": f"Configuration initialized in {destination}",
    }


def _copy_config_file(target: Path, *, overwrite: bool) -> bool:
    """Copy the bundled config.yaml to target. Returns True if copied."""
    if target.exists() and not overwrite:
        return False

    source = resources.files("video_agent_skill").joinpath(DEFAULT_CONFIG_FILENAME)
    try:
        text = source.read_text(encoding="utf-8")
    except OSError:
        text = _generate_default_config()

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise InvalidArgumentError(f"Unable to write config file: {target}") from exc
    return True


def _copy_prompt_file(
    package_dir: Any, target: Path, name: str, *, overwrite: bool
) -> bool:
    """Copy a prompt file from package to target. Returns True if copied."""
    if target.exists() and not overwrite:
        return False
    try:
        text = package_dir.joinpath(name).read_text(encoding="utf-8")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    except OSError as exc:
        raise InvalidArgumentError(f"Unable to write prompt file: {target}") from exc
    return True


def _generate_default_config() -> str:
    """Generate a minimal default config.yaml content."""
    return """system:
  temp_dir: ""
  auto_cleanup: true

network:
  default_proxy: ""
  rules: []

ai:
  asr:
    device: "auto"
    model: "iic/SenseVoiceSmall"
    source_dir: ""
  llm:
    api_base: "https://api.minimaxi.com/v1"
    model_name: "MiniMax-M2.7"
    api_key: ""
    timeout_seconds: 60
    system_prompt: ""
    user_prompt_template: ""

output:
  format: "json"
  file: ""
  batch_separator: "---"
"""


def find_config_file() -> Path | None:
    """Find the config file to load.

    Search order:
    1. Current directory ./config.yaml (project-level override)
    2. Bundled package config.yaml (default, pip-uninstallable)

    CLI parameters override individual fields at a higher layer.
    """
    # 1. Current directory (project-level override)
    cwd_config = Path.cwd() / DEFAULT_CONFIG_FILENAME
    if cwd_config.exists():
        return cwd_config

    # 2. Bundled package config (default)
    bundled = get_default_config_path()
    if bundled.exists():
        return bundled
    return None
