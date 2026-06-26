from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import yaml

from video_agent_skill.errors import InvalidArgumentError

# Default LLM configuration (MiniMax CN)
DEFAULT_LLM_API_BASE = "https://api.minimaxi.com/v1"
DEFAULT_LLM_MODEL = "MiniMax-M2.7"
# Built-in default key for development only. Do not package in production releases.
# IMPORTANT: This key must be removed before production builds.
DEFAULT_LLM_API_KEY = ""


@dataclass(frozen=True)
class SystemConfig:
    temp_dir: str = ""
    auto_cleanup: bool = True


@dataclass(frozen=True)
class ProxyRule:
    domains: list[str] = field(default_factory=list)
    proxy: str = "direct"


@dataclass(frozen=True)
class NetworkConfig:
    default_proxy: str = ""
    timeout_seconds: int = 60
    max_retries: int = 3
    rules: list[ProxyRule] = field(default_factory=list)


@dataclass(frozen=True)
class AsrConfig:
    device: str = "auto"
    model: str = "iic/SenseVoiceSmall"
    source_dir: str = ""


@dataclass(frozen=True)
class LlmConfig:
    api_base: str = DEFAULT_LLM_API_BASE
    model_name: str = DEFAULT_LLM_MODEL
    api_key: str = ""
    timeout_seconds: int = 60
    system_prompt: str = ""
    user_prompt_template: str = ""
    danmaku_prompt: str = ""


@dataclass(frozen=True)
class AiConfig:
    asr: AsrConfig = field(default_factory=AsrConfig)
    llm: LlmConfig = field(default_factory=LlmConfig)


@dataclass(frozen=True)
class OutputConfig:
    format: str = "json"
    file: str = ""
    batch_separator: str = "---"


@dataclass(frozen=True)
class AppConfig:
    system: SystemConfig = field(default_factory=SystemConfig)
    network: NetworkConfig = field(default_factory=NetworkConfig)
    ai: AiConfig = field(default_factory=AiConfig)
    output: OutputConfig = field(default_factory=OutputConfig)


@dataclass(frozen=True)
class CliOverrides:
    proxy: str | None = None
    llm_api_key: str | None = None
    llm_api_base: str | None = None
    llm_model: str | None = None
    llm_system_prompt: str | None = None
    llm_system_prompt_file: str | None = None
    llm_user_prompt_template: str | None = None
    llm_user_prompt_file: str | None = None
    llm_danmaku_prompt: str | None = None
    llm_danmaku_prompt_file: str | None = None
    asr_device: str | None = None
    sensevoice_source_dir: str | None = None


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load config from file.

    Search order when path is None (delegates to find_config_file):
    1. Current directory ./config.yaml (project-level override)
    2. Bundled package config.yaml (default)

    CLI parameter overrides are applied at a higher layer (resolve_* functions).

    The optional path argument is only used by --config CLI flag for explicit
    override.
    """
    if path is not None:
        config_path = Path(path)
        if config_path.exists():
            raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            return parse_config(raw)
        return AppConfig()

    from video_agent_skill.config_init import find_config_file
    found = find_config_file()
    if found is not None:
        raw = yaml.safe_load(found.read_text(encoding="utf-8")) or {}
        return parse_config(raw)

    return AppConfig()


def parse_config(raw: dict[str, object]) -> AppConfig:
    system_raw = _as_mapping(raw.get("system"))
    network_raw = _as_mapping(raw.get("network"))
    ai_raw = _as_mapping(raw.get("ai"))
    asr_raw = _as_mapping(ai_raw.get("asr"))
    llm_raw = _as_mapping(ai_raw.get("llm"))
    output_raw = _as_mapping(raw.get("output"))

    rules = []
    for item in _as_list(network_raw.get("rules")):
        rule_raw = _as_mapping(item)
        rules.append(
            ProxyRule(
                domains=[str(domain) for domain in _as_list(rule_raw.get("domains"))],
                proxy=str(rule_raw.get("proxy") or "direct"),
            )
        )

    return AppConfig(
        system=SystemConfig(
            temp_dir=str(system_raw.get("temp_dir") or ""),
            auto_cleanup=bool(system_raw.get("auto_cleanup", True)),
        ),
        network=NetworkConfig(
            default_proxy=str(network_raw.get("default_proxy") or ""),
            timeout_seconds=_as_int(network_raw.get("timeout_seconds"), default=60),
            max_retries=_as_int(network_raw.get("max_retries"), default=3),
            rules=rules,
        ),
        ai=AiConfig(
            asr=AsrConfig(
                device=str(asr_raw.get("device") or "auto"),
                model=str(asr_raw.get("model") or "iic/SenseVoiceSmall"),
                source_dir=str(asr_raw.get("source_dir") or ""),
            ),
            llm=LlmConfig(
                api_base=str(llm_raw.get("api_base") or DEFAULT_LLM_API_BASE),
                model_name=str(llm_raw.get("model_name") or DEFAULT_LLM_MODEL),
                api_key=str(llm_raw.get("api_key") or ""),
                timeout_seconds=_as_int(llm_raw.get("timeout_seconds"), default=60),
                system_prompt=str(llm_raw.get("system_prompt") or ""),
                user_prompt_template=str(llm_raw.get("user_prompt_template") or ""),
                danmaku_prompt=str(llm_raw.get("danmaku_prompt") or ""),
            ),
        ),
        output=OutputConfig(
            format=str(output_raw.get("format") or "json"),
            file=str(output_raw.get("file") or ""),
            batch_separator=str(output_raw.get("batch_separator") or "---"),
        ),
    )


def resolve_proxy(url: str, config: AppConfig, override_proxy: str | None = None) -> str:
    if override_proxy:
        return override_proxy

    host = (urlparse(url).hostname or "").lower()
    for rule in config.network.rules:
        if any(_domain_matches(host, domain) for domain in rule.domains):
            return rule.proxy
    return config.network.default_proxy


def resolve_llm_config(config: AppConfig, overrides: CliOverrides | None = None) -> LlmConfig:
    overrides = overrides or CliOverrides()
    return LlmConfig(
        api_base=(
            overrides.llm_api_base
            or config.ai.llm.api_base
            or DEFAULT_LLM_API_BASE
        ),
        model_name=(
            overrides.llm_model
            or config.ai.llm.model_name
            or DEFAULT_LLM_MODEL
        ),
        api_key=(
            overrides.llm_api_key
            or config.ai.llm.api_key
            or DEFAULT_LLM_API_KEY
        ),
        timeout_seconds=config.ai.llm.timeout_seconds,
        system_prompt=_resolve_text_setting(
            direct=overrides.llm_system_prompt,
            file_path=overrides.llm_system_prompt_file,
            config_value=config.ai.llm.system_prompt,
            default_file="default-system.txt",
        ),
        user_prompt_template=_resolve_text_setting(
            direct=overrides.llm_user_prompt_template,
            file_path=overrides.llm_user_prompt_file,
            config_value=config.ai.llm.user_prompt_template,
            default_file="default-video-summary.txt",
        ),
        danmaku_prompt=_resolve_text_setting(
            direct=overrides.llm_danmaku_prompt,
            file_path=overrides.llm_danmaku_prompt_file,
            config_value=config.ai.llm.danmaku_prompt,
            default_file="default-danmaku.txt",
        ),
    )


def resolve_asr_device_config(config: AppConfig, overrides: CliOverrides | None = None) -> str:
    overrides = overrides or CliOverrides()
    return resolve_asr_config(config, overrides).device


def resolve_asr_config(config: AppConfig, overrides: CliOverrides | None = None) -> AsrConfig:
    overrides = overrides or CliOverrides()
    return AsrConfig(
        device=(
            overrides.asr_device
            or config.ai.asr.device
            or "auto"
        ),
        model=config.ai.asr.model,
        source_dir=(
            overrides.sensevoice_source_dir
            or config.ai.asr.source_dir
            or ""
        ),
    )


def _domain_matches(host: str, domain: str) -> bool:
    normalized = domain.lower().lstrip(".")
    return host == normalized or host.endswith(f".{normalized}")


def _as_mapping(value: object) -> dict[str, object]:
    return value if isinstance(value, dict) else {}


def _as_list(value: object) -> list[object]:
    return value if isinstance(value, list) else []


def _as_int(value: object, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except (TypeError, ValueError):
        return default


def _resolve_text_setting(
    *,
    direct: str | None,
    file_path: str | None,
    config_value: str,
    default_file: str = "",
) -> str:
    if direct:
        return direct
    if file_path:
        return _read_text_setting_file(file_path)
    if config_value:
        return config_value
    # Fall back to prompt templates: current directory first, then package.
    if default_file:
        # 1. Current directory ./prompts/ (project-level override)
        cwd_prompt = Path.cwd() / "prompts" / default_file
        if cwd_prompt.exists():
            try:
                return cwd_prompt.read_text(encoding="utf-8")
            except OSError:
                pass
        # 2. Bundled package prompt template
        from importlib import resources

        try:
            return resources.files("video_agent_skill").joinpath(
                "prompts", default_file
            ).read_text(encoding="utf-8")
        except OSError:
            pass
    return config_value


def _read_text_setting_file(file_path: str) -> str:
    try:
        return Path(file_path).read_text(encoding="utf-8").strip()
    except OSError as exc:
        raise InvalidArgumentError(f"Unable to read prompt file: {file_path}") from exc
