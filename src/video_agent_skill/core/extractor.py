from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from html import unescape
from pathlib import Path
from re import sub
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from video_agent_skill.core.transcriber import SenseVoiceOptions, transcribe_audio
from video_agent_skill.errors import (
    AuthRequiredError,
    NetworkError,
    SubtitleParseError,
    UnsupportedUrlError,
)
from video_agent_skill.utils.cache import get_cached_file, set_cached_file
from video_agent_skill.utils.config import AsrConfig
from video_agent_skill.utils.logging import info

# Prefer local yt-dlp-fix over system yt-dlp for Bilibili patches
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_YTDLP_FIX = _PROJECT_ROOT / "yt-dlp-fix"
if str(_YTDLP_FIX) not in sys.path and _YTDLP_FIX.exists():
    sys.path.insert(0, str(_YTDLP_FIX))


@dataclass(frozen=True)
class ExtractionResult:
    strategy_used: str
    text: str
    duration_seconds: int | None = None


@dataclass(frozen=True)
class SubtitleCandidate:
    language: str
    url: str
    ext: str
    is_automatic: bool


LANGUAGE_ALIASES = {
    "zh": ["zh", "zh-Hans", "zh-Hant", "zh-CN", "zh-TW", "zh-cn", "zh-tw"],
    "en": ["en", "en-US", "en-GB", "en-us", "en-gb"],
    "ja": ["ja", "ja-JP", "ja-jp"],
    "ko": ["ko", "ko-KR", "ko-kr"],
    "vi": ["vi", "vi-VN", "vi-vn"],
    "fr": ["fr", "fr-FR", "fr-CA", "fr-fr", "fr-ca"],
    "de": ["de", "de-DE", "de-de"],
    "es": ["es", "es-ES", "es-MX", "es-es", "es-mx"],
    "pt": ["pt", "pt-BR", "pt-PT", "pt-br", "pt-pt"],
    "ru": ["ru", "ru-RU", "ru-ru"],
    "th": ["th", "th-TH", "th-th"],
    "ar": ["ar", "ar-SA", "ar-sa"],
    "it": ["it", "it-IT", "it-it"],
}
YDL_NETWORK_OPTIONS = {
    "socket_timeout": 120,
    "retries": 3,
    "fragment_retries": 5,
    "extractor_retries": 3,
    "file_access_retries": 3,
}


def _get_ydl_options(timeout_seconds: int = 60, max_retries: int = 3) -> dict[str, Any]:
    """Get yt-dlp network options with configurable connection timeout.

    socket_timeout controls connection timeout only.
    Download progress is handled by yt-dlp's internal progress tracking.

    Args:
        timeout_seconds: Connection timeout in seconds (default 60).
        max_retries: Maximum number of retries for failed downloads (default 3).
    """
    return {
        "socket_timeout": timeout_seconds,
        "retries": max_retries,
        "fragment_retries": max_retries + 2,
        "extractor_retries": max_retries,
        "file_access_retries": max_retries,
    }


def extract_text_from_url(
    url: str,
    *,
    _language: str,
    _proxy: str = "",
    _work_dir: str | Path | None = None,
    _asr: AsrConfig | None = None,
    _use_cache: bool = True,
    _timeout_seconds: int = 60,
    _max_retries: int = 3,
) -> ExtractionResult:
    _validate_url(url)

    # Check cache first
    if _use_cache:
        cached = get_cached_file(url)
        if cached is not None:
            info(f"Using cached result for {url}")
            return ExtractionResult(
                strategy_used=cached.get("strategy_used", "subtitle"),
                text=cached.get("text", ""),
                duration_seconds=cached.get("duration_seconds"),
            )

    video_info = _probe_video_info(url, proxy=_proxy, timeout_seconds=_timeout_seconds, max_retries=_max_retries)
    candidate = choose_subtitle(video_info, _language)
    if candidate is None:
        work_dir = Path(_work_dir) if _work_dir is not None else Path.cwd()
        asr_config = _asr or AsrConfig()
        audio_path = _download_audio_as_wav(url, work_dir=work_dir, proxy=_proxy, timeout_seconds=_timeout_seconds, max_retries=_max_retries)
        text = transcribe_audio(
            str(audio_path),
            configured_device=asr_config.device,
            options=SenseVoiceOptions(
                model=asr_config.model,
                source_dir=asr_config.source_dir,
                language=_language or "auto",
            ),
        )
        result = ExtractionResult(
            strategy_used="asr",
            text=text,
            duration_seconds=_extract_duration_seconds(video_info),
        )
    else:
        raw_subtitle = fetch_subtitle_text(candidate.url, proxy=_proxy)
        text = clean_subtitle_text(raw_subtitle, ext=candidate.ext)
        if not text:
            raise SubtitleParseError("Subtitle was downloaded but no readable text was extracted.")
        result = ExtractionResult(
            strategy_used="subtitle",
            text=text,
            duration_seconds=_extract_duration_seconds(video_info),
        )

    # Cache the result (text only, never audio)
    if _use_cache:
        set_cached_file(url, {
            "strategy_used": result.strategy_used,
            "text": result.text,
            "duration_seconds": result.duration_seconds,
        })

    return result


def choose_subtitle(info: dict[str, Any], language: str) -> SubtitleCandidate | None:
    preferred_languages = expand_language_preferences(language)
    for is_automatic, key in ((False, "subtitles"), (True, "automatic_captions")):
        subtitle_map = info.get(key) if isinstance(info.get(key), dict) else {}
        for preferred in preferred_languages:
            entries = subtitle_map.get(preferred)
            if not entries or not isinstance(entries, list):
                continue
            # Filter valid entries and prefer vtt format
            valid_entries = [
                entry for entry in entries
                if isinstance(entry, dict) and entry.get("url")
            ]
            if not valid_entries:
                continue
            # Sort by format preference: vtt > json3 > others
            def format_priority(entry: dict) -> int:
                ext = entry.get("ext", "").lower()
                if ext == "vtt":
                    return 0
                if ext == "json3":
                    return 1
                return 2
            sorted_entries = sorted(valid_entries, key=format_priority)
            best = sorted_entries[0]
            return SubtitleCandidate(
                language=preferred,
                url=best["url"],
                ext=best.get("ext", "vtt"),
                is_automatic=is_automatic,
            )
    return None


def expand_language_preferences(language: str) -> list[str]:
    normalized = language.lower().strip()
    aliases = LANGUAGE_ALIASES.get(normalized, [normalized])
    return [normalized] + [a for a in aliases if a != normalized]


def clean_subtitle_text(raw: str, *, ext: str = "") -> str:
    ext_lower = (ext or "").lower()
    if ext_lower == "json3":
        return _clean_json3_subtitle(raw)
    if ext_lower in ("vtt", "webvtt"):
        return _clean_vtt_text(raw)
    # Auto-detect VTT format
    if raw.strip().startswith("WEBVTT"):
        return _clean_vtt_text(raw)
    return _clean_plain_text(raw)


def _clean_vtt_text(raw: str) -> str:
    lines = raw.splitlines()
    result: list[str] = []
    seen: set[str] = set()
    skip_note_block = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("WEBVTT"):
            continue
        if " --> " in stripped and stripped[0].isdigit():
            skip_note_block = False
            continue
        if stripped.startswith("NOTE"):
            skip_note_block = True
            continue
        if skip_note_block:
            continue
        if stripped:
            # Remove HTML tags and decode entities
            cleaned = sub(r"<[^>]+>", "", stripped)
            cleaned = unescape(cleaned)
            cleaned = cleaned.strip()
            if cleaned and cleaned not in seen:
                seen.add(cleaned)
                result.append(cleaned)
    return "\n".join(result)


def _clean_json3_subtitle(raw: str) -> str:
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SubtitleParseError("Invalid JSON3 subtitle format.") from exc

    events = data.get("events", []) if isinstance(data, dict) else []
    if not isinstance(events, list):
        raise SubtitleParseError("Invalid JSON3 subtitle format: missing events.")

    texts: list[str] = []
    seen: set[str] = set()
    for event in events:
        if not isinstance(event, dict):
            continue
        segs = event.get("segs", [])
        if not isinstance(segs, list):
            continue
        line_parts: list[str] = []
        for seg in segs:
            if isinstance(seg, dict) and "utf8" in seg:
                line_parts.append(str(seg["utf8"]))
        if line_parts:
            line = "".join(line_parts)
            # Remove HTML tags and decode entities
            line = sub(r"<[^>]+>", "", line)
            line = unescape(line)
            if line and line not in seen:
                seen.add(line)
                texts.append(line)

    if not texts:
        raise SubtitleParseError("JSON3 subtitle contains no readable text.")

    return "\n".join(texts)


def _clean_plain_text(raw: str) -> str:
    cleaned = sub(r"<[^>]+>", "", raw)
    cleaned = unescape(cleaned)
    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    return " ".join(lines)


def fetch_subtitle_text(url: str, *, proxy: str = "") -> str:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
    }
    req = Request(url, headers=headers)
    try:
        if proxy and proxy != "direct":
            import urllib.request

            proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
            opener = urllib.request.build_opener(proxy_handler)
            with opener.open(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
        else:
            with urlopen(req, timeout=30) as resp:
                return resp.read().decode("utf-8")
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise AuthRequiredError("Subtitle download requires authorization.") from exc
        raise NetworkError(f"Subtitle download failed with HTTP {exc.code}.") from exc
    except URLError as exc:
        raise NetworkError(f"Subtitle download failed: {exc.reason}.") from exc


def _apply_anticrawler_handlers(url: str, ydl_opts: dict[str, Any]) -> dict[str, Any]:
    """Apply all matching anti-crawler handlers to yt-dlp options.
    
    Loads built-in BilibiliAntiCrawlerHandler and any third-party handlers.
    """
    from video_agent_skill.core.anticrawler import BilibiliAntiCrawlerHandler
    from video_agent_skill.core.plugin_registry import PluginRegistry
    
    registry = PluginRegistry.instance()
    handlers = registry.get_anticrawler_handlers(url)
    
    builtin_handler = BilibiliAntiCrawlerHandler()
    if builtin_handler.supports(url):
        handlers.append(builtin_handler)
    
    for handler in handlers:
        ydl_opts = handler.apply(ydl_opts)
    
    return ydl_opts


def _probe_video_info(url: str, *, proxy: str = "", timeout_seconds: int = 60, max_retries: int = 3) -> dict[str, Any]:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise NetworkError("yt-dlp is not installed.") from exc

    ydl_opts: dict[str, Any] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "writeautomaticsub": True,
        "http_headers": _default_http_headers(url),
        **_get_ydl_options(timeout_seconds=timeout_seconds, max_retries=max_retries),
    }
    if proxy and proxy != "direct":
        ydl_opts["proxy"] = proxy

    ydl_opts = _apply_anticrawler_handlers(url, ydl_opts)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        message = str(exc)
        if _looks_auth_required(message):
            auth_message = "Target video requires login, membership, or authorization."
            raise AuthRequiredError(auth_message) from exc
        detail = _short_error_message(message)
        raise NetworkError(f"Failed to probe video metadata: {detail}") from exc

    if not isinstance(info, dict):
        raise NetworkError("yt-dlp returned an invalid metadata response.")
    return info


def _download_audio_as_wav(url: str, *, work_dir: Path, proxy: str = "", timeout_seconds: int = 60, max_retries: int = 3) -> Path:
    try:
        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise NetworkError("yt-dlp is not installed.") from exc

    work_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(work_dir / "%(id)s.%(ext)s")
    ydl_opts: dict[str, Any] = {
        "format": "bestaudio/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "http_headers": _default_http_headers(url),
        **_get_ydl_options(timeout_seconds=timeout_seconds, max_retries=max_retries),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
    }
    if proxy and proxy != "direct":
        ydl_opts["proxy"] = proxy

    ydl_opts = _apply_anticrawler_handlers(url, ydl_opts)

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
    except Exception as exc:
        message = str(exc)
        if _looks_auth_required(message):
            raise AuthRequiredError("Target video requires login or authorization.") from exc
        detail = _short_error_message(message)
        raise NetworkError(f"Audio download failed: {detail}") from exc

    if not isinstance(info, dict):
        raise NetworkError("yt-dlp returned an invalid metadata response.")

    video_id = info.get("id", "audio")
    wav_path = work_dir / f"{video_id}.wav"
    if wav_path.exists():
        return wav_path

    # Fallback: find any .wav in work_dir
    wav_files = list(work_dir.glob("*.wav"))
    if wav_files:
        return wav_files[0]

    raise NetworkError("Audio download completed but .wav file not found.")


def _default_http_headers(url: str) -> dict[str, str]:
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-us,en;q=0.5",
    }
    if "bilibili.com" in urlparse(url).netloc:
        headers["Origin"] = "https://www.bilibili.com"
        headers["Referer"] = "https://www.bilibili.com/"
    return headers


def _get_bilibili_cookie_file() -> str:
    """Generate a temporary cookie file with buvid3/buvid4 fingerprint
    to bypass Bilibili HTTP 412.
    """
    import tempfile
    import uuid

    try:
        import json as _json
        from urllib.request import Request, urlopen

        req = Request(
            "https://api.bilibili.com/x/frontend/finger/spi",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                "Referer": "https://www.bilibili.com/",
            },
        )
        with urlopen(req, timeout=10) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
        buvid3 = data.get("data", {}).get("b_3", "")
        buvid4 = data.get("data", {}).get("b_4", "")
    except Exception:
        buvid3 = ""
        buvid4 = ""

    # If API fails, generate a random buvid3
    if not buvid3:
        buvid3 = f"{uuid.uuid4().hex.upper()}infoc"

    cookie_content = f"""# Netscape HTTP Cookie File
# https://curl.haxx.se/rfc/cookie_spec.html
# This is a generated file!  Do not edit.

.bilibili.com	TRUE	/	FALSE	0	buvid3	{buvid3}
"""
    if buvid4:
        cookie_content += f".bilibili.com	TRUE	/	FALSE	0	buvid4	{buvid4}\n"

    fd, path = tempfile.mkstemp(suffix=".txt")
    with os.fdopen(fd, "w") as f:
        f.write(cookie_content)
    return path


def _extract_duration_seconds(info: dict[str, Any]) -> int | None:
    duration = info.get("duration")
    if isinstance(duration, (int, float)):
        return int(duration)
    return None


def _looks_auth_required(message: str) -> bool:
    lower = message.lower()
    return any(
        keyword in lower
        for keyword in [
            "login",
            "member",
            "auth",
            "sign in",
            "private",
            "restricted",
            "http error 403",
            "error 403",
        ]
    )


def _short_error_message(message: str) -> str:
    lines = message.strip().splitlines()
    first = lines[0] if lines else message
    if len(first) > 200:
        first = first[:200] + "..."
    return first


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        raise UnsupportedUrlError(f"Invalid URL format: {url}")
    supported_schemes = {"http", "https"}
    if parsed.scheme not in supported_schemes:
        raise UnsupportedUrlError(f"Unsupported URL scheme: {parsed.scheme}")
