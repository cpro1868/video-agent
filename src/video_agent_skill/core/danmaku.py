#!/usr/bin/env python3
"""Danmaku (bullet comment) extraction and analysis for Bilibili videos.

Usage:
    from video_agent_skill.core.danmaku import extract_danmaku, analyze_danmaku
    danmaku_list = extract_danmaku(video_url, proxy=proxy)
    analysis = analyze_danmaku(danmaku_list, video_context, llm_config)
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.request import Request, urlopen

from video_agent_skill.errors import NetworkError
from video_agent_skill.utils.config import LlmConfig


@dataclass(frozen=True)
class DanmakuItem:
    """Single danmaku comment."""

    text: str
    time: float  # seconds from video start
    mode: int  # 1=scroll, 4=bottom, 5=top, 6=reverse, 7=advanced, 8=code, 9=BAS
    color: str
    size: int
    timestamp: int  # unix timestamp
    pool: int  # 0=normal, 1=subtitle, 2=special
    user_hash: str  # anonymized user id
    dm_id: int  # danmaku id
    # Popularity metrics (if available from API)
    likes: int = 0
    weight: int = 0  # Bilibili's internal weight score


@dataclass(frozen=True)
class DanmakuAnalysis:
    """Analysis result of danmaku comments."""

    sentiment: str  # positive/negative/neutral/mixed
    sentiment_score: int  # 1-10
    hot_topics: list[dict[str, Any]]
    top_liked: list[str]
    controversial: list[str]
    interesting: list[str]
    audience_profile: str
    content_relation: str
    markdown: str = ""


def extract_danmaku(video_url: str, *, proxy: str = "") -> list[DanmakuItem]:
    """Extract danmaku from Bilibili video using yt-dlp.

    Returns empty list if no danmaku available or not a Bilibili URL.
    """
    if "bilibili.com" not in video_url:
        return []

    try:
        import sys
        from pathlib import Path

        # Prefer local yt-dlp-fix for Bilibili patches
        _PROJECT_ROOT = Path(__file__).resolve().parents[3]
        _YTDLP_FIX = _PROJECT_ROOT / "yt-dlp-fix"
        if str(_YTDLP_FIX) not in sys.path and _YTDLP_FIX.exists():
            sys.path.insert(0, str(_YTDLP_FIX))

        from yt_dlp import YoutubeDL
    except ImportError as exc:
        raise NetworkError("yt-dlp is not installed.") from exc

    # Import cookie helper from extractor module
    from video_agent_skill.core.extractor import _get_bilibili_cookie_file

    ydl_opts: dict[str, Any] = {
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "writesubtitles": True,
        "subtitleslangs": ["danmaku"],
        "subtitlesformat": "xml",
        "cookiefile": _get_bilibili_cookie_file(),
        "http_headers": {
            "Origin": "https://www.bilibili.com",
            "Referer": "https://www.bilibili.com/",
        },
        "socket_timeout": 30,
        "retries": 3,
    }
    if proxy and proxy != "direct":
        ydl_opts["proxy"] = proxy

    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
    except Exception:
        # Danmaku extraction is optional, return empty on failure
        return []

    if not isinstance(info, dict):
        return []

    # Get danmaku subtitle URL
    subtitles = info.get("subtitles", {})
    if not isinstance(subtitles, dict):
        return []

    danmaku_entries = subtitles.get("danmaku")
    if not danmaku_entries or not isinstance(danmaku_entries, list):
        return []

    # Download danmaku XML
    danmaku_url = danmaku_entries[0].get("url")
    if not danmaku_url:
        return []

    try:
        danmaku_xml = _download_text(danmaku_url, proxy=proxy)
    except Exception:
        return []

    return _parse_danmaku_xml(danmaku_xml)


def _download_text(url: str, *, proxy: str = "") -> str:
    """Download text from URL, handling compression."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.bilibili.com/",
        "Accept-Encoding": "gzip, deflate",  # Tell server we accept compression
    }
    req = Request(url, headers=headers)
    
    if proxy and proxy != "direct":
        import urllib.request

        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(proxy_handler)
        with opener.open(req, timeout=30) as resp:
            raw = resp.read()
    else:
        with urlopen(req, timeout=30) as resp:
            raw = resp.read()
    
    # Check if data is compressed
    try:
        import zlib
        # Try deflate decompression (with -15 wbits for raw deflate)
        decompressed = zlib.decompress(raw, -15)
        return decompressed.decode("utf-8")
    except Exception:
        pass
    
    # Try gzip
    try:
        import gzip
        decompressed = gzip.decompress(raw)
        return decompressed.decode("utf-8")
    except Exception:
        pass
    
    # Fallback: try as plain text with different encodings
    for enc in ["utf-8", "gbk", "gb2312", "latin-1"]:
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    
    # Last resort
    return raw.decode("utf-8", errors="ignore")


def _parse_danmaku_xml(xml_content: str) -> list[DanmakuItem]:
    """Parse Bilibili danmaku XML format."""
    items: list[DanmakuItem] = []
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return items

    for d in root.findall("d"):
        text = d.text or ""
        if not text.strip():
            continue

        # Parse attributes: p="time,mode,size,color,timestamp,pool,user_hash,dm_id,weight"
        p_attr = d.get("p", "")
        parts = p_attr.split(",")

        try:
            time = float(parts[0]) if len(parts) > 0 else 0.0
            mode = int(parts[1]) if len(parts) > 1 else 1
            size = int(parts[2]) if len(parts) > 2 else 25
            color = parts[3] if len(parts) > 3 else "16777215"
            timestamp = int(parts[4]) if len(parts) > 4 else 0
            pool = int(parts[5]) if len(parts) > 5 else 0
            user_hash = parts[6] if len(parts) > 6 else ""
            dm_id = int(parts[7]) if len(parts) > 7 else 0
            weight = int(parts[8]) if len(parts) > 8 else 0
        except (ValueError, IndexError):
            continue

        items.append(
            DanmakuItem(
                text=text,
                time=time,
                mode=mode,
                color=color,
                size=size,
                timestamp=timestamp,
                pool=pool,
                user_hash=user_hash,
                dm_id=dm_id,
                weight=weight,
            )
        )

    return items


def filter_representative_danmaku(
    items: list[DanmakuItem], max_count: int = 100
) -> list[DanmakuItem]:
    """Filter and sort danmaku by relevance and popularity.

    Strategy:
    1. Remove duplicates (same text)
    2. Sort by weight (Bilibili's internal score) descending
    3. Take top max_count
    """
    # Deduplicate by text, keep highest weight
    seen: dict[str, DanmakuItem] = {}
    for item in items:
        if item.text in seen:
            if item.weight > seen[item.text].weight:
                seen[item.text] = item
        else:
            seen[item.text] = item

    # Sort by weight descending, then by time
    unique = sorted(seen.values(), key=lambda x: (-x.weight, x.time))

    return unique[:max_count]


def format_danmaku_for_llm(items: list[DanmakuItem]) -> str:
    """Format danmaku list for LLM prompt."""
    if not items:
        return "无弹幕数据"

    lines = [f"共 {len(items)} 条代表性弹幕：\n"]
    for i, item in enumerate(items, 1):
        time_str = f"{int(item.time // 60)}:{int(item.time % 60):02d}"
        lines.append(f"{i}. [{time_str}] {item.text}")

    return "\n".join(lines)


def analyze_danmaku(
    items: list[DanmakuItem],
    video_title: str,
    video_summary: str,
    *,
    _llm: LlmConfig,
    _prompt_template: str = "",
) -> DanmakuAnalysis:
    """Analyze danmaku using LLM.

    If _prompt_template is empty, use default danmaku prompt.
    """
    if not items:
        return DanmakuAnalysis(
            sentiment="无数据",
            sentiment_score=0,
            hot_topics=[],
            top_liked=[],
            controversial=[],
            interesting=[],
            audience_profile="无弹幕数据",
            content_relation="无弹幕数据",
            markdown="## 弹幕分析\n\n无弹幕数据",
        )

    from video_agent_skill.core.summarizer import _post_chat_completion

    # Load default prompt if not provided
    if not _prompt_template:
        _prompt_template = _load_default_danmaku_prompt()

    danmaku_text = format_danmaku_for_llm(items)

    # Build prompt
    user_content = f"""视频标题：{video_title}

视频摘要：{video_summary}

弹幕列表：
{danmaku_text}
"""

    # Use LLM to analyze
    try:
        payload = {
            "model": _llm.model_name,
            "messages": [
                {"role": "system", "content": _prompt_template},
                {"role": "user", "content": user_content},
            ],
            "max_tokens": 2000,
        }
        response = _post_chat_completion(_llm, payload)
        markdown = _extract_assistant_markdown(response)
    except Exception as exc:
        return DanmakuAnalysis(
            sentiment="分析失败",
            sentiment_score=0,
            hot_topics=[],
            top_liked=[],
            controversial=[],
            interesting=[],
            audience_profile=f"LLM分析失败: {exc}",
            content_relation="分析失败",
            markdown=f"## 弹幕分析\n\n分析失败: {exc}",
        )

    # Parse markdown to structured data (simplified)
    return _parse_danmaku_markdown(markdown, raw_markdown=markdown)


def _load_default_danmaku_prompt() -> str:
    """Load default danmaku prompt from package."""
    from video_agent_skill.prompt_files import get_prompt_info

    info = get_prompt_info()
    # Try to find danmaku prompt
    for key, path in info.items():
        if "danmaku" in key.lower():
            try:
                return Path(path).read_text(encoding="utf-8")
            except OSError:
                pass
    return _DEFAULT_DANMAKU_PROMPT


_DEFAULT_DANMAKU_PROMPT = (
    "你是一位弹幕分析专家。请分析视频弹幕，提取大众反应、情感倾向和热点话题。"
    "请输出：整体情感（正面/负面/中性/混合，1-10分）、热点话题（最多5个，带热度）、"
    "代表性评论（高赞5条、争议3条、有趣3条）、观众画像、与视频内容的关联。"
    "注意：弹幕可能含网络用语，情感可能两极分化，注意识别反讽幽默。"
    "弹幕太少请说明'弹幕样本不足'。"
)


def _extract_assistant_markdown(response: dict[str, Any]) -> str:
    """Extract markdown text from LLM response."""
    choices = response.get("choices", [])
    if not choices:
        return ""
    content = choices[0].get("message", {}).get("content", "")
    return content.strip()


def _parse_danmaku_markdown(
    markdown: str, *, raw_markdown: str = ""
) -> DanmakuAnalysis:
    """Parse danmaku analysis markdown to structured data."""
    # Simple extraction - in production would use more robust parsing
    sentiment = "中性"
    sentiment_score = 5

    # Try to extract sentiment
    if "正面" in markdown or "positive" in markdown.lower():
        sentiment = "正面"
        sentiment_score = 7
    elif "负面" in markdown or "negative" in markdown.lower():
        sentiment = "负面"
        sentiment_score = 3
    elif "混合" in markdown:
        sentiment = "混合"
        sentiment_score = 5

    # Extract sections
    hot_topics = []
    top_liked = []
    controversial = []
    interesting = []

    lines = markdown.split("\n")
    current_section = ""

    for line in lines:
        line = line.strip()
        if line.startswith("## 热点话题") or line.startswith("### 热点话题"):
            current_section = "hot_topics"
        elif line.startswith("## 代表性评论") or line.startswith("### 代表性评论"):
            current_section = "comments"
        elif line.startswith("## 观众画像") or line.startswith("### 观众画像"):
            current_section = "audience"
        elif line.startswith("## 内容关联") or line.startswith("### 内容关联"):
            current_section = "relation"
        elif line.startswith("- ") or line.startswith("* "):
            if current_section == "hot_topics":
                hot_topics.append({"topic": line[2:], "heat": "中", "examples": []})
            elif current_section == "comments":
                if "高赞" in line or "点赞" in line:
                    top_liked.append(line[2:])
                elif "争议" in line:
                    controversial.append(line[2:])
                elif "有趣" in line or "幽默" in line:
                    interesting.append(line[2:])

    # Extract audience profile and content relation
    audience_profile = "观众关注视频内容，积极参与讨论"
    content_relation = "弹幕与视频内容高度相关"

    # Try to find these sections
    audience_match = re.search(
        r"(?:##|###)\s*观众画像\s*\n(.*?)(?=\n##|\Z)", markdown, re.DOTALL
    )
    if audience_match:
        audience_profile = audience_match.group(1).strip()[:500]

    relation_match = re.search(
        r"(?:##|###)\s*(?:内容关联|与视频内容的关联)\s*\n(.*?)(?=\n##|\Z)",
        markdown,
        re.DOTALL,
    )
    if relation_match:
        content_relation = relation_match.group(1).strip()[:500]

    return DanmakuAnalysis(
        sentiment=sentiment,
        sentiment_score=sentiment_score,
        hot_topics=hot_topics,
        top_liked=top_liked[:5],
        controversial=controversial[:3],
        interesting=interesting[:3],
        audience_profile=audience_profile,
        content_relation=content_relation,
        markdown=raw_markdown or markdown,
    )
