from __future__ import annotations

import json
from io import BytesIO
from typing import Any
from urllib.error import HTTPError

import pytest

from video_agent_skill.core import summarizer
from video_agent_skill.errors import LlmSafetyRefusalError, LlmTimeoutError, OutputContractError
from video_agent_skill.utils.config import LlmConfig


class FakeHeaders:
    def get_content_charset(self) -> str:
        return "utf-8"


class FakeResponse:
    headers = FakeHeaders()

    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload

    def __enter__(self) -> FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return json.dumps(self.payload).encode("utf-8")


def test_summarize_text_posts_openai_compatible_payload(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '# Test Video Summary\n\n'
                        '## 视频摘要\n\n'
                        'A concise summary.\n\n'
                        '## 核心要点\n\n'
                        '1. **One**: First point\n'
                        '2. **Two**: Second point\n'
                        '3. **Three**: Third point\n\n'
                        '## 标签\n\n'
                        'AI、Video\n\n'
                        '## 原文摘录\n\n'
                        '> Transcript excerpt'
                    )
                }
            }
        ]
    }

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["url"] = request.full_url
        captured["headers"] = dict(request.header_items())
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse(api_payload)

    monkeypatch.setattr(summarizer, "urlopen", fake_urlopen)

    content = summarizer.summarize_text(
        "Transcript text",
        _language="en",
        _llm=LlmConfig(
            api_base="http://localhost:11434/v1",
            model_name="qwen2.5",
            api_key="secret",
            timeout_seconds=12,
        ),
    )

    assert captured["url"] == "http://localhost:11434/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["timeout"] == 12
    assert captured["body"]["model"] == "qwen2.5"
    # response_format removed for Markdown output
    assert "response_format" not in captured["body"]
    assert content.summary == "A concise summary."
    assert content.key_points == ["One: First point", "Two: Second point", "Three: Third point"]
    assert content.tags == ["AI", "Video"]


def test_summarize_text_requests_simplified_chinese(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "简体中文摘要。",
                            "key_points": ["一", "二", "三"],
                            "tags": ["视频"],
                            "transcript_excerpt": "片段",
                        }
                    )
                }
            }
        ]
    }

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(api_payload)

    monkeypatch.setattr(summarizer, "urlopen", fake_urlopen)

    summarizer.summarize_text(
        "Transcript text",
        _language="zh",
        _llm=LlmConfig(api_key="test-key"),
    )

    user_prompt = captured["body"]["messages"][1]["content"]
    assert "Simplified Chinese" in user_prompt
    assert "必须使用简体中文输出" in user_prompt
    assert "do not use Traditional Chinese" in user_prompt


def test_summarize_text_truncates_long_chinese_summary(monkeypatch) -> None:
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "中" * 240,
                            "key_points": ["一", "二", "三"],
                            "tags": [],
                            "transcript_excerpt": "片段",
                        }
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    content = summarizer.summarize_text(
        "Transcript text",
        _language="zh",
        _llm=LlmConfig(api_key="test-key"),
    )

    # Legacy JSON mode: summary is truncated to 200 chars
    assert len(content.summary) == 200


def test_summarize_text_truncates_long_markdown_summary(monkeypatch) -> None:
    long_summary = "这是一段很长的摘要。" * 50
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        f'# 测试视频\n\n'
                        f'## 视频摘要\n\n'
                        f'{long_summary}\n\n'
                        f'## 核心要点\n\n'
                        f'1. **要点一**: 解释一\n'
                        f'2. **要点二**: 解释二\n'
                        f'3. **要点三**: 解释三\n\n'
                        f'## 标签\n\n'
                        f'测试\n\n'
                        f'## 原文摘录\n\n'
                        f'> 原文片段'
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    content = summarizer.summarize_text(
        "Transcript text",
        _language="zh",
        _llm=LlmConfig(api_key="test-key"),
    )

    # Markdown mode: no truncation, full summary preserved
    assert len(content.summary) > 200
    assert "这是一段很长的摘要。" in content.summary


def test_summarize_text_uses_configured_prompts(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Summary",
                            "key_points": ["One", "Two", "Three"],
                            "tags": [],
                            "transcript_excerpt": "Excerpt",
                        }
                    )
                }
            }
        ]
    }

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(api_payload)

    monkeypatch.setattr(summarizer, "urlopen", fake_urlopen)

    summarizer.summarize_text(
        "Transcript text",
        _language="zh",
        _llm=LlmConfig(
            api_key="test-key",
            system_prompt="Custom system",
            user_prompt_template=(
                "Return JSON in {output_language}. {language_instruction}\n{transcript}"
            ),
        ),
    )

    messages = captured["body"]["messages"]
    assert messages[0]["content"] == "Custom system"
    assert "Transcript text" in messages[1]["content"]
    assert "Simplified Chinese" in messages[1]["content"]


def test_summarize_text_rejects_unknown_prompt_placeholder() -> None:
    with pytest.raises(OutputContractError):
        summarizer.summarize_text(
            "Transcript text",
            _language="en",
            _llm=LlmConfig(user_prompt_template="Bad placeholder: {unknown}"),
        )


def test_summarize_text_allows_literal_json_braces_in_prompt(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Summary",
                            "key_points": ["One", "Two", "Three"],
                            "tags": [],
                            "transcript_excerpt": "Excerpt",
                        }
                    )
                }
            }
        ]
    }

    def fake_urlopen(request: Any, timeout: int) -> FakeResponse:
        captured["body"] = json.loads(request.data.decode("utf-8"))
        return FakeResponse(api_payload)

    monkeypatch.setattr(summarizer, "urlopen", fake_urlopen)

    summarizer.summarize_text(
        "Transcript text",
        _language="en",
        _llm=LlmConfig(
            api_key="test-key",
            user_prompt_template=(
                'Return {"summary":"...", "key_points":[]} from {transcript}.'
            ),
        ),
    )

    prompt = captured["body"]["messages"][1]["content"]
    assert '{"summary":"...", "key_points":[]}' in prompt
    assert "Transcript text" in prompt


def test_summarize_text_prefers_valid_json_when_model_echoes_schema(monkeypatch) -> None:
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '# Final Summary\n\n'
                        '## 视频摘要\n\n'
                        'Summary\n\n'
                        '## 核心要点\n\n'
                        '1. **One**: First point\n'
                        '2. **Two**: Second point\n'
                        '3. **Three**: Third point\n\n'
                        '## 标签\n\n'
                        'demo\n\n'
                        '## 原文摘录\n\n'
                        '> Excerpt'
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    content = summarizer.summarize_text(
        "Source transcript.",
        _language="en",
        _llm=LlmConfig(api_key="test-key"),
    )

    assert content.summary == "Summary"
    assert content.key_points == ["One: First point", "Two: Second point", "Three: Third point"]
    assert content.tags == ["demo"]
    assert content.transcript_excerpt == "Excerpt"


def test_summarize_text_uses_source_excerpt_when_missing(monkeypatch) -> None:
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Summary",
                            "key_points": ["One", "Two", "Three"],
                            "tags": [],
                        }
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    content = summarizer.summarize_text(
        "Source transcript for fallback excerpt.",
        _language="en",
        _llm=LlmConfig(api_key="test-key"),
    )

    assert content.transcript_excerpt == "Source transcript for fallback excerpt."


def test_summarize_text_extracts_json_after_think_and_markdown(monkeypatch) -> None:
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": (
                        '<think>{"summary":"draft","key_points":[]}</think>\n'
                        "```json\n"
                        '{"summary":"Summary","key_points":["One","Two","Three"],'
                        '"tags":["demo"],"transcript_excerpt":"Excerpt"}\n'
                        "```"
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    content = summarizer.summarize_text(
        "Source transcript.",
        _language="en",
        _llm=LlmConfig(api_key="test-key"),
    )

    assert content.summary == "Summary"
    assert content.key_points == ["One", "Two", "Three"]
    assert content.tags == ["demo"]


def test_summarize_text_maps_timeout(monkeypatch) -> None:
    def fake_urlopen(*_args: object, **_kwargs: object) -> FakeResponse:
        raise TimeoutError("timed out")

    monkeypatch.setattr(summarizer, "urlopen", fake_urlopen)

    with pytest.raises(LlmTimeoutError):
        summarizer.summarize_text(
            "Transcript",
            _language="en",
            _llm=LlmConfig(api_key="test-key"),
        )


def test_summarize_text_maps_llm_safety_refusal(monkeypatch) -> None:
    error_body = (
        b'{"type":"error","error":{"type":"unprocessable_entity_error",'
        b'"message":"output new_sensitive (1027)","http_code":"422"}}'
    )

    def fake_urlopen(*_args: object, **_kwargs: object) -> FakeResponse:
        raise HTTPError(
            url="https://api.example.com/v1/chat/completions",
            code=422,
            msg="Unprocessable Entity",
            hdrs={},
            fp=BytesIO(error_body),
        )

    monkeypatch.setattr(summarizer, "urlopen", fake_urlopen)

    with pytest.raises(LlmSafetyRefusalError):
        summarizer.summarize_text("Transcript", _language="zh", _llm=LlmConfig(api_key="test-key"))


def test_summarize_text_rejects_invalid_message_json(monkeypatch) -> None:
    api_payload = {"choices": [{"message": {"content": "not-json"}}]}
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    with pytest.raises(OutputContractError):
        summarizer.summarize_text("Transcript", _language="en", _llm=LlmConfig())


def test_summarize_text_rejects_wrong_key_points_count(monkeypatch) -> None:
    api_payload = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "summary": "Summary",
                            "key_points": ["Only one"],
                            "tags": [],
                        }
                    )
                }
            }
        ]
    }
    monkeypatch.setattr(summarizer, "urlopen", lambda *_args, **_kwargs: FakeResponse(api_payload))

    with pytest.raises(OutputContractError):
        summarizer.summarize_text("Transcript", _language="en", _llm=LlmConfig())
