from __future__ import annotations

import sys
import types

import pytest

from video_agent_skill.core import extractor
from video_agent_skill.errors import (
    SubtitleParseError,
    UnsupportedUrlError,
)
from video_agent_skill.utils.config import AsrConfig


def test_language_preferences_expand_common_chinese_aliases() -> None:
    assert extractor.expand_language_preferences("zh") == [
        "zh",
        "zh-Hans",
        "zh-Hant",
        "zh-CN",
        "zh-TW",
        "zh-cn",
        "zh-tw",
    ]


def test_choose_subtitle_prefers_manual_over_automatic() -> None:
    info = {
        "subtitles": {"zh-Hans": [{"url": "https://example.com/manual.vtt", "ext": "vtt"}]},
        "automatic_captions": {"zh": [{"url": "https://example.com/auto.vtt", "ext": "vtt"}]},
    }

    candidate = extractor.choose_subtitle(info, "zh")

    assert candidate is not None
    assert candidate.url == "https://example.com/manual.vtt"
    assert candidate.language == "zh-Hans"
    assert candidate.is_automatic is False


def test_choose_subtitle_prefers_vtt_format() -> None:
    info = {
        "subtitles": {
            "en": [
                {"url": "https://example.com/caption.json3", "ext": "json3"},
                {"url": "https://example.com/caption.vtt", "ext": "vtt"},
            ]
        }
    }

    candidate = extractor.choose_subtitle(info, "en")

    assert candidate is not None
    assert candidate.url == "https://example.com/caption.vtt"


def test_choose_subtitle_ignores_bilibili_danmaku() -> None:
    info = {"subtitles": {"danmaku": [{"url": "https://example.com/danmaku.xml", "ext": "xml"}]}}

    assert extractor.choose_subtitle(info, "zh") is None


def test_clean_subtitle_text_strips_vtt_noise_and_deduplicates() -> None:
    raw = """WEBVTT

00:00:01.000 --> 00:00:02.000 align:start position:0%
<v Speaker> Hello &amp; welcome </v>

00:00:02.000 --> 00:00:03.000
<c.colorE5E5E5>Hello &amp; welcome</c>

NOTE internal marker
this should be skipped

00:00:03.000 --> 00:00:04.000
Second line
"""

    assert extractor.clean_subtitle_text(raw) == "Hello & welcome\nSecond line"


def test_clean_json3_subtitle_text() -> None:
    raw = """
    {
      "events": [
        {"segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
        {"segs": [{"utf8": "Hello "}, {"utf8": "world"}]},
        {"segs": [{"utf8": "<b>Second</b> line"}]}
      ]
    }
    """

    assert extractor.clean_subtitle_text(raw, ext="json3") == "Hello world\nSecond line"


def test_invalid_json3_subtitle_fails() -> None:
    with pytest.raises(SubtitleParseError):
        extractor.clean_subtitle_text("not-json", ext="json3")


def test_invalid_url_fails_before_probe() -> None:
    with pytest.raises(UnsupportedUrlError):
        extractor.extract_text_from_url("not-a-url", _language="zh")


def test_incomplete_read_is_not_auth_required() -> None:
    message = (
        "ERROR: [BiliBili] 1XDLn6XEWK: Unable to download webpage: "
        "74039 bytes read (caused by <IncompleteRead: 74039 bytes read>)"
    )

    assert extractor._looks_auth_required(message) is False


def test_explicit_forbidden_error_is_auth_required() -> None:
    assert extractor._looks_auth_required("Unable to download webpage: HTTP Error 403") is True


def test_extract_text_from_url_uses_subtitle_path(monkeypatch) -> None:
    monkeypatch.setattr(
        extractor,
        "_probe_video_info",
        lambda url, proxy="": {
            "duration": 42,
            "subtitles": {"en": [{"url": "https://example.com/caption.vtt", "ext": "vtt"}]},
        },
    )
    monkeypatch.setattr(
        extractor,
        "fetch_subtitle_text",
        lambda url, proxy="": "WEBVTT\n\n00:00:01.000 --> 00:00:02.000\nExtracted caption",
    )

    result = extractor.extract_text_from_url(
        "https://example.com/video", _language="en", _use_cache=False
    )

    assert result.strategy_used == "subtitle"
    assert result.text == "Extracted caption"
    assert result.duration_seconds == 42


def test_extract_text_from_url_uses_asr_fallback(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    monkeypatch.setattr(
        extractor,
        "_probe_video_info",
        lambda url, proxy="": {"duration": 42, "subtitles": {}, "automatic_captions": {}},
    )
    monkeypatch.setattr(
        extractor,
        "_download_audio_as_wav",
        lambda url, work_dir, proxy="": work_dir / "audio.wav",
    )

    def fake_transcribe_audio(
        audio_path: str, *, configured_device: str, options: object
    ) -> str:
        captured["audio_path"] = audio_path
        captured["configured_device"] = configured_device
        captured["options"] = options
        return "ASR transcript"

    monkeypatch.setattr(extractor, "transcribe_audio", fake_transcribe_audio)

    result = extractor.extract_text_from_url(
        "https://example.com/video",
        _language="en",
        _work_dir=tmp_path,
        _asr=AsrConfig(device="cpu", model="asr-model", source_dir="G:/SenseVoice"),
        _use_cache=False,
    )

    assert result.strategy_used == "asr"
    assert result.text == "ASR transcript"
    assert captured["configured_device"] == "cpu"
    assert captured["audio_path"].endswith("audio.wav")  # type: ignore[union-attr]


def test_download_audio_as_wav_uses_yt_dlp_postprocessor(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            captured["options"] = options

        def __enter__(self) -> FakeYoutubeDL:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def extract_info(self, url: str, *, download: bool) -> dict[str, object]:
            captured["url"] = url
            captured["download"] = download
            (tmp_path / "abc.wav").write_bytes(b"wav")
            return {"id": "abc"}

    fake_module = types.SimpleNamespace(YoutubeDL=FakeYoutubeDL)
    monkeypatch.setitem(sys.modules, "yt_dlp", fake_module)

    audio_path = extractor._download_audio_as_wav(
        "https://example.com/video", work_dir=tmp_path, proxy="socks5://127.0.0.1:7890"
    )

    options = captured["options"]
    assert audio_path == tmp_path / "abc.wav"
    assert captured["download"] is True
    assert options["format"] == "bestaudio/best"  # type: ignore[index]
    assert options["proxy"] == "socks5://127.0.0.1:7890"  # type: ignore[index]
    assert options["socket_timeout"] == 60  # type: ignore[index]
    assert options["retries"] == 3  # type: ignore[index]
    assert options["fragment_retries"] == 5  # type: ignore[index]
    assert options["extractor_retries"] == 3  # type: ignore[index]
    assert options["file_access_retries"] == 3  # type: ignore[index]
    assert options["postprocessors"][0]["preferredcodec"] == "wav"  # type: ignore[index]


def test_probe_video_info_uses_network_retry_options(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeYoutubeDL:
        def __init__(self, options: dict[str, object]) -> None:
            captured["options"] = options

        def __enter__(self) -> FakeYoutubeDL:
            return self

        def __exit__(self, *_args: object) -> None:
            return None

        def extract_info(self, url: str, *, download: bool) -> dict[str, object]:
            return {"duration": 1}

    fake_module = types.SimpleNamespace(YoutubeDL=FakeYoutubeDL)
    monkeypatch.setitem(sys.modules, "yt_dlp", fake_module)

    extractor._probe_video_info("https://example.com/video")

    options = captured["options"]
    assert options["socket_timeout"] == 60  # type: ignore[index]
    assert options["retries"] == 3  # type: ignore[index]
    assert options["fragment_retries"] == 5  # type: ignore[index]
    assert options["extractor_retries"] == 3  # type: ignore[index]
