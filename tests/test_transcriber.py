from __future__ import annotations

import sys
import types
import wave

import pytest

from video_agent_skill.core import transcriber
from video_agent_skill.errors import AsrRuntimeError, CudaOomError


def test_auto_device_falls_back_to_cpu(monkeypatch) -> None:
    monkeypatch.setattr(transcriber, "_cuda_available", lambda: False)
    monkeypatch.setattr(transcriber, "_mps_available", lambda: False)

    assert transcriber.select_asr_device("auto") == "cpu"


def test_auto_device_prefers_cuda(monkeypatch) -> None:
    monkeypatch.setattr(transcriber, "_cuda_available", lambda: True)
    monkeypatch.setattr(transcriber, "_mps_available", lambda: True)

    assert transcriber.select_asr_device("auto") == "cuda"


def test_explicit_unavailable_device_fails(monkeypatch) -> None:
    monkeypatch.setattr(transcriber, "_cuda_available", lambda: False)

    with pytest.raises(AsrRuntimeError):
        transcriber.select_asr_device("cuda")


def test_invalid_device_fails() -> None:
    with pytest.raises(AsrRuntimeError):
        transcriber.select_asr_device("gpu")


def test_clean_asr_text_removes_sensevoice_tags() -> None:
    assert transcriber.clean_asr_text("<|zh|><|NEUTRAL|> 你好 世界 ") == "你好 世界"


def test_split_wav_by_duration_creates_chunks(tmp_path) -> None:
    wav_path = tmp_path / "sample.wav"
    with wave.open(str(wav_path), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(10)
        writer.writeframes(b"\x00\x00" * 25)

    chunks = transcriber.split_wav_by_duration(wav_path, tmp_path / "chunks", max_seconds=1)

    assert [chunk.name for chunk in chunks] == [
        "sample.part0000.wav",
        "sample.part0001.wav",
        "sample.part0002.wav",
    ]


def test_transcribe_audio_uses_funasr_automodel(monkeypatch, tmp_path) -> None:
    captured: dict[str, object] = {}

    class FakeModel:
        def generate(self, **kwargs: object) -> list[dict[str, str]]:
            captured["generate"] = kwargs
            return [{"text": "<|en|><|NEUTRAL|> hello world"}]

    class FakeAutoModel:
        def __new__(cls, **kwargs: object) -> FakeModel:
            captured["model"] = kwargs
            return FakeModel()

    fake_funasr = types.SimpleNamespace(AutoModel=FakeAutoModel)
    monkeypatch.setitem(sys.modules, "funasr", fake_funasr)
    monkeypatch.setattr(transcriber, "_cuda_available", lambda: True)

    text = transcriber.transcribe_audio(
        str(tmp_path / "audio.wav"),
        configured_device="cuda",
        options=transcriber.SenseVoiceOptions(language="en"),
    )

    assert text == "hello world"
    assert captured["model"]["device"] == "cuda:0"  # type: ignore[index]
    assert captured["model"]["vad_model"] == "fsmn-vad"  # type: ignore[index]
    assert captured["generate"]["language"] == "en"  # type: ignore[index]


def test_transcribe_audio_maps_cuda_oom(monkeypatch, tmp_path) -> None:
    class FakeModel:
        def generate(self, **_kwargs: object) -> list[dict[str, str]]:
            raise RuntimeError("CUDA out of memory")

    class FakeAutoModel:
        def __new__(cls, **_kwargs: object) -> FakeModel:
            return FakeModel()

    monkeypatch.setitem(sys.modules, "funasr", types.SimpleNamespace(AutoModel=FakeAutoModel))

    with pytest.raises(CudaOomError):
        transcriber.transcribe_audio(str(tmp_path / "audio.wav"), configured_device="cpu")


def test_transcribe_audio_requires_funasr(monkeypatch, tmp_path) -> None:
    monkeypatch.delitem(sys.modules, "funasr", raising=False)
    monkeypatch.setattr(transcriber, "find_spec", lambda name: None)

    with pytest.raises(AsrRuntimeError):
        transcriber.transcribe_audio(str(tmp_path / "audio.wav"), configured_device="cpu")
