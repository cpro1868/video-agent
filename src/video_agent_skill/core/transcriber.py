from __future__ import annotations

import re
import wave
from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from typing import Any

from video_agent_skill.errors import AsrRuntimeError, CudaOomError
from video_agent_skill.utils.logging import debug, info, warning

VALID_ASR_DEVICES = {"auto", "cuda", "mps", "cpu"}
TAG_PATTERN = re.compile(r"<\|.*?\|>")


@dataclass(frozen=True)
class SenseVoiceOptions:
    model: str = "iic/SenseVoiceSmall"
    source_dir: str = ""
    language: str = "auto"
    use_itn: bool = True
    max_single_segment_ms: int = 30_000
    batch_size_s: int = 60
    merge_vad: bool = True
    merge_length_s: int = 15


def select_asr_device(configured_device: str) -> str:
    device = configured_device.lower().strip()
    if device not in VALID_ASR_DEVICES:
        raise AsrRuntimeError(
            f"Unsupported ASR device '{configured_device}'. Expected auto, cuda, mps, or cpu."
        )

    if device == "auto":
        if _cuda_available():
            return "cuda"
        if _mps_available():
            return "mps"
        return "cpu"

    if device == "cuda" and not _cuda_available():
        raise AsrRuntimeError("ASR device cuda is configured but unavailable.")
    if device == "mps" and not _mps_available():
        raise AsrRuntimeError("ASR device mps is configured but unavailable.")
    return device


def transcribe_audio(
    audio_path: str,
    *,
    configured_device: str = "auto",
    options: SenseVoiceOptions | None = None,
) -> str:
    selected_device = select_asr_device(configured_device)
    options = options or SenseVoiceOptions()
    info(f"ASR: Loading SenseVoice model on device={selected_device}, model={options.model}")
    model = _load_sensevoice_model(options, selected_device)
    try:
        info(f"ASR: Transcribing audio={audio_path}")
        result = model.generate(
            input=audio_path,
            cache={},
            language=options.language,
            use_itn=options.use_itn,
            batch_size_s=options.batch_size_s,
            merge_vad=options.merge_vad,
            merge_length_s=options.merge_length_s,
        )
        debug("ASR: Transcription completed successfully")
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            warning(f"ASR: GPU OOM on device={selected_device}")
            raise CudaOomError("ASR inference failed because GPU memory is insufficient.") from exc
        warning(f"ASR: Runtime error during inference: {exc}")
        raise AsrRuntimeError(f"ASR inference failed: {exc.__class__.__name__}.") from exc
    except Exception as exc:
        warning(f"ASR: Unexpected error during inference: {exc}")
        raise AsrRuntimeError(f"ASR inference failed: {exc.__class__.__name__}.") from exc

    text = clean_asr_text(_extract_text_from_generate_result(result))
    info(f"ASR: Transcription complete, text_length={len(text)} chars")
    return text


def split_wav_by_duration(
    audio_path: str | Path,
    output_dir: str | Path,
    *,
    max_seconds: int = 30,
) -> list[Path]:
    source = Path(audio_path)
    if source.suffix.lower() != ".wav":
        raise AsrRuntimeError("Audio slicing currently expects a .wav file.")
    if max_seconds <= 0:
        raise AsrRuntimeError("max_seconds must be greater than zero.")

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)

    with wave.open(str(source), "rb") as reader:
        params = reader.getparams()
        frames_per_chunk = int(reader.getframerate() * max_seconds)
        if frames_per_chunk <= 0:
            raise AsrRuntimeError("Invalid WAV frame rate.")

        chunks: list[Path] = []
        index = 0
        while True:
            frames = reader.readframes(frames_per_chunk)
            if not frames:
                break
            chunk_path = destination / f"{source.stem}.part{index:04d}.wav"
            with wave.open(str(chunk_path), "wb") as writer:
                writer.setparams(params)
                writer.writeframes(frames)
            chunks.append(chunk_path)
            index += 1
    return chunks


def clean_asr_text(text: str) -> str:
    without_tags = TAG_PATTERN.sub("", text)
    return re.sub(r"\s+", " ", without_tags).strip()


def _load_sensevoice_model(options: SenseVoiceOptions, selected_device: str) -> Any:
    try:
        from funasr import AutoModel
    except ImportError as exc:
        raise AsrRuntimeError(
            "FunASR is not installed in the current Python environment. "
            "Run this command in the configured SenseVoice environment."
        ) from exc

    device = _to_funasr_device(selected_device)
    kwargs: dict[str, Any] = {
        "model": options.model,
        "trust_remote_code": False,
        "vad_model": "fsmn-vad",
        "vad_kwargs": {"max_single_segment_time": options.max_single_segment_ms},
        "device": device,
    }
    remote_code = _remote_code_path(options.source_dir)
    if remote_code is not None:
        kwargs["trust_remote_code"] = True
        kwargs["remote_code"] = str(remote_code)

    try:
        return AutoModel(**kwargs)
    except RuntimeError as exc:
        if "out of memory" in str(exc).lower():
            message = "ASR model loading failed because GPU memory is insufficient."
            raise CudaOomError(message) from exc
        raise AsrRuntimeError(f"ASR model loading failed: {exc.__class__.__name__}.") from exc
    except Exception as exc:
        raise AsrRuntimeError(f"ASR model loading failed: {exc.__class__.__name__}.") from exc


def _extract_text_from_generate_result(result: object) -> str:
    if not isinstance(result, list) or not result:
        raise AsrRuntimeError("ASR result was empty.")
    texts: list[str] = []
    for item in result:
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            texts.append(item["text"])
    if not texts:
        raise AsrRuntimeError("ASR result did not contain text.")
    return " ".join(texts)


def _remote_code_path(source_dir: str) -> Path | None:
    if not source_dir:
        return None
    candidate = Path(source_dir) / "model.py"
    return candidate if candidate.exists() else None


def _to_funasr_device(selected_device: str) -> str:
    if selected_device == "cuda":
        return "cuda:0"
    return selected_device


def _cuda_available() -> bool:
    if find_spec("torch") is None:
        return False
    import torch

    return bool(torch.cuda.is_available())


def _mps_available() -> bool:
    if find_spec("torch") is None:
        return False
    import torch

    return bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available())
