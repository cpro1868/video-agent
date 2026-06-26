"""Result cache for video text extraction.

Caches extracted transcripts (subtitles or ASR results) keyed by URL,
avoiding redundant downloads and processing. Only text is cached,
never audio or video files.

Provides two cache layers:
1. In-memory cache (get_cached/set_cached) with explicit TTL
2. File-based cache (get_cached_url/set_cached_url) with configurable TTL via env
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

from video_agent_skill.utils.logging import debug, info, warning

DEFAULT_CACHE_DIR = Path.home() / ".video_agent_skill" / "cache"
DEFAULT_CACHE_TTL_SECONDS = 7 * 24 * 3600  # 7 days

_memory_cache: dict[str, dict[str, Any]] = {}


def _url_to_key(url: str) -> str:
    """Generate a cache key from URL."""
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:32]


def _get_cache_dir() -> Path:
    """Get cache directory from env or default."""
    env_dir = os.environ.get("VIDEO_AGENT_CACHE_DIR", "")
    if env_dir:
        return Path(env_dir)
    return DEFAULT_CACHE_DIR


def _get_cache_ttl() -> int:
    """Get cache TTL from env or default (seconds)."""
    env_ttl = os.environ.get("VIDEO_AGENT_CACHE_TTL", "")
    try:
        return int(env_ttl) if env_ttl else DEFAULT_CACHE_TTL_SECONDS
    except ValueError:
        return DEFAULT_CACHE_TTL_SECONDS


def set_cached(key: str, value: Any, ttl: int = 3600) -> None:
    """Set cached value with TTL in seconds."""
    _memory_cache[key] = {"value": value, "expires": time.time() + ttl}


def get_cached(key: str) -> Any | None:
    """Get cached value if not expired."""
    if key in _memory_cache:
        entry = _memory_cache[key]
        if time.time() < entry["expires"]:
            return entry["value"]
        del _memory_cache[key]
    return None


def get_cached_file(url: str) -> dict[str, Any] | None:
    """Retrieve cached extraction result for URL if valid.

    Returns None if not cached or expired.
    """
    cache_dir = _get_cache_dir()
    key = _url_to_key(url)
    cache_file = cache_dir / f"{key}.json"

    if not cache_file.exists():
        return None

    ttl = _get_cache_ttl()
    if ttl > 0:
        age = time.time() - cache_file.stat().st_mtime
        if age > ttl:
            debug(f"Cache expired for {url} (age={age:.0f}s, ttl={ttl}s)")
            return None

    try:
        data = json.loads(cache_file.read_text(encoding="utf-8"))
        info(f"Cache hit for {url}")
        return data
    except (OSError, json.JSONDecodeError) as exc:
        warning(f"Cache read failed for {url}: {exc}")
        return None


def set_cached_file(url: str, result: dict[str, Any]) -> None:
    """Store extraction result in cache."""
    cache_dir = _get_cache_dir()
    cache_dir.mkdir(parents=True, exist_ok=True)
    key = _url_to_key(url)
    cache_file = cache_dir / f"{key}.json"

    try:
        cache_file.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        debug(f"Cached result for {url}")
    except OSError as exc:
        warning(f"Cache write failed for {url}: {exc}")


def clear_cache() -> int:
    """Clear all cached entries. Returns number of files removed."""
    cache_dir = _get_cache_dir()
    if not cache_dir.exists():
        return 0

    count = 0
    for f in cache_dir.glob("*.json"):
        try:
            f.unlink()
            count += 1
        except OSError:
            pass
    return count


def get_cache_stats() -> dict[str, int]:
    """Get cache statistics."""
    cache_dir = _get_cache_dir()
    if not cache_dir.exists():
        return {"entries": 0, "total_size_bytes": 0}

    entries = list(cache_dir.glob("*.json"))
    total_size = sum(f.stat().st_size for f in entries if f.exists())
    return {"entries": len(entries), "total_size_bytes": total_size}
