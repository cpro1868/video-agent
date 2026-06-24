from __future__ import annotations

from video_agent_skill.errors import InvalidArgumentError
from video_agent_skill.utils.config import (
    CliOverrides,
    parse_config,
    resolve_asr_config,
    resolve_asr_device_config,
    resolve_llm_config,
    resolve_proxy,
)


def test_proxy_rule_matches_subdomain() -> None:
    config = parse_config(
        {
            "network": {
                "default_proxy": "direct",
                "rules": [
                    {"domains": ["youtube.com", "youtu.be"], "proxy": "socks5://127.0.0.1:7890"}
                ],
            }
        }
    )

    assert resolve_proxy("https://www.youtube.com/watch?v=abc", config) == (
        "socks5://127.0.0.1:7890"
    )
    assert resolve_proxy("https://example.com/watch?v=abc", config) == "direct"


def test_cli_proxy_override_wins() -> None:
    config = parse_config({"network": {"default_proxy": "direct"}})

    assert resolve_proxy("https://example.com", config, "http://proxy.local:8080") == (
        "http://proxy.local:8080"
    )


def test_llm_resolution_order_cli_over_config() -> None:
    config = parse_config(
        {"ai": {"llm": {"api_base": "http://config/v1", "model_name": "config-model"}}}
    )

    resolved = resolve_llm_config(
        config,
        CliOverrides(llm_api_base="http://cli/v1", llm_model="cli-model"),
    )

    assert resolved.api_base == "http://cli/v1"
    assert resolved.model_name == "cli-model"


def test_llm_prompt_resolution_from_config_and_cli_file(tmp_path) -> None:
    prompt_file = tmp_path / "prompt.txt"
    prompt_file.write_text("prompt from file {transcript}", encoding="utf-8")
    config = parse_config(
        {
            "ai": {
                "llm": {
                    "system_prompt": "system from config",
                    "user_prompt_template": "user from config {transcript}",
                }
            }
        }
    )

    resolved = resolve_llm_config(
        config,
        CliOverrides(llm_user_prompt_file=str(prompt_file)),
    )

    assert resolved.system_prompt == "system from config"
    assert resolved.user_prompt_template == "prompt from file {transcript}"


def test_llm_prompt_file_read_failure_is_invalid_argument() -> None:
    config = parse_config({})

    try:
        resolve_llm_config(config, CliOverrides(llm_user_prompt_file="missing-prompt.txt"))
    except InvalidArgumentError as exc:
        assert "Unable to read prompt file" in str(exc)
    else:
        raise AssertionError("Expected InvalidArgumentError")


def test_asr_device_resolution_cli_over_config() -> None:
    config = parse_config({"ai": {"asr": {"device": "cpu"}}})

    assert resolve_asr_device_config(config) == "cpu"
    assert resolve_asr_device_config(config, CliOverrides(asr_device="cuda")) == "cuda"


def test_sensevoice_source_dir_resolution_cli_over_config() -> None:
    config = parse_config(
        {"ai": {"asr": {"source_dir": "G:/from-config/SenseVoice", "model": "config-model"}}}
    )

    resolved = resolve_asr_config(config)
    assert resolved.source_dir == "G:/from-config/SenseVoice"
    assert resolved.model == "config-model"

    overridden = resolve_asr_config(
        config, CliOverrides(sensevoice_source_dir="G:/from-cli/SenseVoice")
    )
    assert overridden.source_dir == "G:/from-cli/SenseVoice"


def test_output_config_parsing() -> None:
    config = parse_config(
        {
            "output": {
                "format": "markdown",
                "file": "output/summary.md",
                "batch_separator": "===",
            }
        }
    )

    assert config.output.format == "markdown"
    assert config.output.file == "output/summary.md"
    assert config.output.batch_separator == "==="


def test_output_config_defaults() -> None:
    config = parse_config({})

    assert config.output.format == "json"
    assert config.output.file == ""
    assert config.output.batch_separator == "---"
