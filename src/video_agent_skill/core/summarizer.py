from __future__ import annotations

import json
import re
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from video_agent_skill.contracts import ResponseContent
from video_agent_skill.errors import (
    LlmSafetyRefusalError,
    LlmTimeoutError,
    NetworkError,
    OutputContractError,
)
from video_agent_skill.utils.config import LlmConfig
from video_agent_skill.utils.retry import with_retry

DEFAULT_SYSTEM_PROMPT_MARKDOWN = (
    "You are a professional video content analysis assistant for AI Agent workflows. "
    "Your task is to organize video transcripts into structured Markdown summary documents. "
    "Output Markdown directly. Do not wrap output in JSON objects or code fences. "
    "Do not invent facts that are not supported by the transcript."
)
DEFAULT_SYSTEM_PROMPT_JSON = (
    "You are a video transcript structuring engine for AI Agent workflows. "
    "Return only one valid JSON object. "
    "Do not include markdown, explanations, code fences, or extra text. "
    "Do not invent facts that are not supported by the transcript."
)
DEFAULT_USER_PROMPT_TEMPLATE = (
    "Summarize the transcript in {output_language}. "
    "{language_instruction} "
    "Output a structured document with: title, summary, "
    "key_points, detailed_content, tags, transcript_excerpt. "
    "The title must be specific and descriptive, "
    "never use generic titles like 'Video Summary'. "
    "The detailed_content must have 2-4 sections with substantial content.\n\n"
    "Transcript:\n{transcript}"
)
PROMPT_TEMPLATE_KEYS = {
    "output_language",
    "language_instruction",
    "transcript",
    "video_url",
    "video_duration",
    "video_strategy",
    "video_language",
}

# Backward-compatible alias (Markdown is the default format).
DEFAULT_SYSTEM_PROMPT = DEFAULT_SYSTEM_PROMPT_MARKDOWN

# Language code to display name mapping for LLM output
LANGUAGE_DISPLAY_NAMES: dict[str, str] = {
    "zh": "Simplified Chinese",
    "zh-hans": "Simplified Chinese",
    "zh-hant": "Traditional Chinese",
    "zh-cn": "Simplified Chinese",
    "zh-tw": "Traditional Chinese",
    "en": "English",
    "en-us": "English",
    "en-gb": "English",
    "ja": "Japanese",
    "ko": "Korean",
    "vi": "Vietnamese",
    "fr": "French",
    "de": "German",
    "es": "Spanish",
    "pt": "Portuguese",
    "ru": "Russian",
    "th": "Thai",
    "ar": "Arabic",
    "it": "Italian",
}

# Language code to instruction mapping for LLM output
LANGUAGE_INSTRUCTIONS: dict[str, str] = {
    "zh": "必须使用简体中文输出。Use Simplified Chinese characters only.",
    "zh-hans": "必须使用简体中文输出。Use Simplified Chinese characters only.",
    "zh-hant": "必須使用繁體中文輸出。Use Traditional Chinese characters only.",
    "zh-cn": "必须使用简体中文输出。Use Simplified Chinese characters only.",
    "zh-tw": "必須使用繁體中文輸出。Use Traditional Chinese characters only.",
    "en": "Use English.",
    "en-us": "Use English.",
    "en-gb": "Use English (British).",
    "ja": "日本語で出力してください。Use Japanese.",
    "ko": "한국어로 출력하세요. Use Korean.",
    "vi": "Xuất bằng tiếng Việt. Use Vietnamese.",
    "fr": "Sortez en français. Use French.",
    "de": "Auf Deutsch ausgeben. Use German.",
    "es": "Salida en español. Use Spanish.",
    "pt": "Saída em português. Use Portuguese.",
    "ru": "Вывод на русском языке. Use Russian.",
    "th": "เอาต์พุตเป็นภาษาไทย. Use Thai.",
    "ar": "أخرج بالعربية. Use Arabic.",
    "it": "Usa l'italiano. Use Italian.",
}


def _resolve_language_name(language: str) -> str:
    """Resolve a language code to its display name for LLM output."""
    normalized = language.lower().strip()
    if normalized in LANGUAGE_DISPLAY_NAMES:
        return LANGUAGE_DISPLAY_NAMES[normalized]
    # Try prefix match (e.g., "zh-Hans" matches "zh-hans")
    for code, name in LANGUAGE_DISPLAY_NAMES.items():
        if normalized.startswith(code):
            return name
    # Fallback: use the raw code as language name
    return language


def _resolve_language_instruction(language: str) -> str:
    """Resolve a language code to its instruction text for LLM output."""
    normalized = language.lower().strip()
    if normalized in LANGUAGE_INSTRUCTIONS:
        return LANGUAGE_INSTRUCTIONS[normalized]
    # Try prefix match
    for code, instruction in LANGUAGE_INSTRUCTIONS.items():
        if normalized.startswith(code):
            return instruction
    # Fallback: generic instruction
    return f"Use {language}."


def summarize_text(
    text: str,
    *,
    _language: str,
    _llm: LlmConfig,
    _duration_seconds: int | None = None,
    _output_format: str = "markdown",
    _video_url: str = "",
    _video_strategy: str = "",
) -> ResponseContent:
    if not text.strip():
        raise OutputContractError("Cannot summarize empty transcript text.")

    if _output_format not in {"markdown", "json"}:
        raise OutputContractError(
            f"Unsupported output_format '{_output_format}'. Expected 'markdown' or 'json'."
        )

    payload = _build_chat_payload(
        text,
        language=_language,
        llm=_llm,
        output_format=_output_format,
        duration_seconds=_duration_seconds,
        video_url=_video_url,
        video_strategy=_video_strategy,
    )
    effective_timeout = _calculate_timeout(_llm, text, _duration_seconds)

    def _do_summary() -> dict[str, Any]:
        return _post_chat_completion(_llm, payload, timeout_override=effective_timeout)

    response = with_retry(
        _do_summary,
        max_retries=3,
        base_delay=2.0,
        operation_name="LLM summarization",
    )
    content_text = _extract_assistant_markdown(response)

    # Diagnostic: dump LLM raw response when VIDEO_AGENT_DEBUG_LLM=1
    import os
    if os.environ.get("VIDEO_AGENT_DEBUG_LLM") == "1":
        import tempfile
        from pathlib import Path
        debug_dir = Path(tempfile.gettempdir()) / "video_agent_debug"
        debug_dir.mkdir(parents=True, exist_ok=True)
        (debug_dir / "llm_raw_response.json").write_text(
            json.dumps(response, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        (debug_dir / "llm_markdown_content.txt").write_text(
            content_text, encoding="utf-8"
        )
        from video_agent_skill.utils.logging import warning as _warn
        _warn(f"LLM debug dump: {debug_dir / 'llm_markdown_content.txt'}")

    if _output_format == "json":
        return _parse_json_to_content(content_text, source_text=text)
    return _parse_markdown_to_content(content_text, source_text=text)


def _calculate_timeout(
    llm: LlmConfig,
    text: str,
    duration_seconds: int | None = None,
) -> int:
    """Calculate effective LLM timeout based on video duration and text length.

    Base timeout from config, then add:
    - Duration-based: longer videos need more time for LLM to process
    - Text-length-based: very long transcripts need more time
    """
    base = llm.timeout_seconds

    # Duration-based adjustment
    if duration_seconds is not None and duration_seconds > 0:
        if duration_seconds <= 300:  # ≤ 5 min
            duration_add = 0
        elif duration_seconds <= 1800:  # 5-30 min
            duration_add = 60
        elif duration_seconds <= 3600:  # 30 min - 1 hour
            duration_add = 120
        else:  # > 1 hour
            duration_add = 240
    else:
        duration_add = 0

    # Text-length-based adjustment (as fallback or supplement)
    text_len = len(text)
    if text_len > 50000:  # Very long transcript (>50k chars)
        text_add = 60
    elif text_len > 20000:  # Long transcript (>20k chars)
        text_add = 30
    else:
        text_add = 0

    return base + max(duration_add, text_add)


def _build_chat_payload(
    text: str,
    *,
    language: str,
    llm: LlmConfig,
    output_format: str = "markdown",
    duration_seconds: int | None = None,
    video_url: str = "",
    video_strategy: str = "",
) -> dict[str, Any]:
    output_language = _resolve_language_name(language)
    language_instruction = _resolve_language_instruction(language)
    # Select the default system prompt based on the desired output format.
    # If the user has overridden the system prompt via config/CLI, respect it
    # (they are taking responsibility for format alignment themselves).
    if llm.system_prompt:
        system_prompt = llm.system_prompt
    elif output_format == "json":
        system_prompt = DEFAULT_SYSTEM_PROMPT_JSON
    else:
        system_prompt = DEFAULT_SYSTEM_PROMPT_MARKDOWN

    # Format video metadata for prompt injection
    video_duration_str = f"{duration_seconds}秒" if duration_seconds else "未知"

    user_prompt = _render_user_prompt(
        llm.user_prompt_template or DEFAULT_USER_PROMPT_TEMPLATE,
        output_language=output_language,
        language_instruction=language_instruction,
        transcript=text,
        video_url=video_url,
        video_duration=video_duration_str,
        video_strategy=video_strategy or "未知",
        video_language=language,
    )
    return {
        "model": llm.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.3,
    }


def _post_chat_completion(
    llm: LlmConfig,
    payload: dict[str, Any],
    *,
    timeout_override: int | None = None,
) -> dict[str, Any]:
    endpoint = _chat_completions_url(llm.api_base)
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {"Content-Type": "application/json"}
    if llm.api_key:
        headers["Authorization"] = f"Bearer {llm.api_key}"
    else:
        raise OutputContractError(
            "LLM API key is not configured. "
            "Please set it via one of the following methods:\n"
            "  1. Environment variable: VIDEO_AGENT_LLM_API_KEY=<your-key>\n"
            "  2. Command line: --llm-api-key <your-key>\n"
            "  3. config.yaml: ai.llm.api_key\n"
            "Note: The built-in default key is for development only. "
            "Do not package it in production releases."
        )

    request = Request(endpoint, data=body, headers=headers, method="POST")
    effective_timeout = timeout_override if timeout_override is not None else llm.timeout_seconds
    try:
        with urlopen(request, timeout=effective_timeout) as response:
            charset = response.headers.get_content_charset() or "utf-8"
            raw = response.read().decode(charset, errors="replace")
    except TimeoutError as exc:
        raise LlmTimeoutError("LLM request timed out.") from exc
    except HTTPError as exc:
        if exc.code in {408, 504}:
            raise LlmTimeoutError(f"LLM request timed out with HTTP {exc.code}.") from exc
        detail = _read_http_error_detail(exc)
        if _looks_llm_safety_refusal(detail):
            snippet = detail[:150] if detail else ""
            raise LlmSafetyRefusalError(
                "LLM provider refused the request or output for safety policy reasons. "
                f"HTTP {exc.code}. Provider detail: {snippet}"
            ) from exc
        suffix = f": {detail}" if detail else "."
        raise NetworkError(f"LLM request failed with HTTP {exc.code}{suffix}") from exc
    except URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise LlmTimeoutError("LLM request timed out.") from exc
        raise NetworkError(f"LLM request failed: {exc.reason}.") from exc

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise OutputContractError("LLM response was not valid JSON.") from exc
    if not isinstance(parsed, dict):
        raise OutputContractError("LLM response JSON must be an object.")
    return parsed


def _extract_assistant_markdown(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise OutputContractError("LLM response missing choices.")

    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        raise OutputContractError("LLM response choice must be an object.")

    message = first_choice.get("message")
    if not isinstance(message, dict):
        raise OutputContractError("LLM response missing message.")

    content = message.get("content")
    if not isinstance(content, str):
        raise OutputContractError("LLM message content must be a string.")

    # Remove thinking/reasoning tags and content if present
    # Handles various formats: <thinking>...</thinking>, <think>...</think>,
    # [thinking]...[/thinking], <reasoning>...</reasoning>, etc.
    cleaned = content
    # XML-style tags (case-insensitive, multiline)
    for tag in ["thinking", "think", "reasoning", "reason", "thought"]:
        cleaned = re.sub(
            rf"<{tag}\b[^>]*>.*?</{tag}>",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
    # BBCode-style tags
    for tag in ["thinking", "think", "reasoning", "reason", "thought"]:
        cleaned = re.sub(
            rf"\[{tag}\b[^\]]*\].*?\[/{tag}\]",
            "",
            cleaned,
            flags=re.DOTALL | re.IGNORECASE,
        )
    # Markdown code blocks labeled as thinking
    cleaned = re.sub(
        r"```\s*(?:thinking|think|reasoning|reason|thought)\s*\n.*?```",
        "",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )

    return cleaned.strip()


def _parse_json_to_content(content_text: str, *, source_text: str) -> ResponseContent:
    """Parse LLM output as JSON (for output_format=json).

    Tolerant of LLM deviations: key_points count is normalized rather than
    rejected, missing fields are filled with sensible defaults.
    """
    parsed = _extract_json_object(content_text)
    if parsed is None:
        # LLM was asked for JSON but didn't produce one; fall back to Markdown
        # parsing so the user still gets a usable result instead of an error.
        return _parse_markdown_format(content_text, source_text=source_text)

    title = parsed.get("title")
    summary = parsed.get("summary")
    key_points = parsed.get("key_points")
    detailed_content = parsed.get("detailed_content")
    tags = parsed.get("tags")
    transcript_excerpt = parsed.get("transcript_excerpt")

    if not isinstance(title, str) or not title.strip():
        title = "视频内容总结"
    if not isinstance(summary, str) or not summary.strip():
        raise OutputContractError("LLM JSON missing non-empty summary.")

    # Tolerant key_points handling: accept any list of strings, normalize count
    # to 3-5 by truncating or padding, rather than hard-failing.
    normalized_key_points: list[str] = []
    if isinstance(key_points, list):
        for item in key_points:
            if isinstance(item, str) and item.strip():
                normalized_key_points.append(item.strip())
    # Truncate to 5
    normalized_key_points = normalized_key_points[:5]
    # Pad to 3 if fewer
    while len(normalized_key_points) < 3:
        normalized_key_points.append("Key point extraction incomplete")

    normalized_tags: list[str] = []
    if isinstance(tags, list):
        for item in tags:
            if isinstance(item, str) and item.strip():
                normalized_tags.append(item.strip())

    if not isinstance(transcript_excerpt, str) or not transcript_excerpt.strip():
        transcript_excerpt = source_text[:500].strip()

    normalized_detailed_content: list[dict[str, str]] = []
    if isinstance(detailed_content, list):
        for section in detailed_content:
            if isinstance(section, dict):
                section_title = str(section.get("section_title", "")).strip()
                content = str(section.get("content", "")).strip()
                if section_title and content:
                    normalized_detailed_content.append({
                        "section_title": section_title,
                        "content": content,
                    })

    # Truncate long Chinese summary for contract compliance
    normalized_summary = summary.strip()
    if len(normalized_summary) > 200:
        chinese_chars = sum(
            1 for c in normalized_summary if '\u4e00' <= c <= '\u9fff'
        )
        if chinese_chars > len(normalized_summary) * 0.5:
            normalized_summary = normalized_summary[:200].rstrip()

    return ResponseContent(
        title=title.strip(),
        summary=normalized_summary,
        key_points=normalized_key_points,
        detailed_content=normalized_detailed_content,
        tags=normalized_tags,
        transcript_excerpt=transcript_excerpt.strip(),
        markdown=content_text,
    )


def _extract_json_object(text: str) -> dict[str, Any] | None:
    """Extract the first JSON object from text, tolerating code fences."""
    trimmed = text.strip()
    # Direct JSON
    if trimmed.startswith("{"):
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    # JSON in code fence
    match = re.search(r"```(?:json)?\s*\n(\{.+?\})\n```", trimmed, re.DOTALL)
    if match:
        try:
            parsed = json.loads(match.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass
    # Fallback: find first {...} block
    start = trimmed.find("{")
    if start != -1:
        end = trimmed.rfind("}")
        if end > start:
            try:
                parsed = json.loads(trimmed[start : end + 1])
                if isinstance(parsed, dict):
                    return parsed
            except json.JSONDecodeError:
                pass
    return None


def _parse_markdown_to_content(markdown: str, *, source_text: str) -> ResponseContent:
    """Parse Markdown output to extract structured fields.

    Supports both new Markdown format and legacy JSON format for backward compatibility.
    JSON parsing failures fall back to Markdown parsing instead of raising.
    """
    # Try to detect if content is JSON (legacy format)
    trimmed = markdown.strip()
    if trimmed.startswith("{") and trimmed.endswith("}"):
        try:
            parsed = json.loads(trimmed)
            if isinstance(parsed, dict) and "summary" in parsed:
                try:
                    return _parse_json_legacy(
                        parsed, source_text=source_text, raw_markdown=markdown
                    )
                except OutputContractError:
                    # JSON doesn't meet strict legacy constraints; fall back to Markdown
                    pass
        except json.JSONDecodeError:
            pass

    # Also try to extract JSON from markdown code blocks (legacy format)
    json_block_match = re.search(r"```json\s*\n(.+?)\n```", trimmed, re.DOTALL)
    if json_block_match:
        try:
            parsed = json.loads(json_block_match.group(1))
            if isinstance(parsed, dict) and "summary" in parsed:
                try:
                    return _parse_json_legacy(
                        parsed, source_text=source_text, raw_markdown=markdown
                    )
                except OutputContractError:
                    # JSON doesn't meet strict legacy constraints; fall back to Markdown
                    pass
        except json.JSONDecodeError:
            pass

    # Parse as Markdown format
    return _parse_markdown_format(markdown, source_text=source_text)


def _parse_markdown_format(markdown: str, *, source_text: str) -> ResponseContent:
    """Parse new Markdown format."""
    # Extract title from first # heading
    title_match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "视频内容总结"

    # Extract summary from ## 视频摘要 section
    summary = _extract_section_content(markdown, "视频摘要")
    if not summary:
        summary = _extract_section_content(markdown, "摘要")
    if not summary:
        # Fallback: extract first paragraph after title
        paragraphs = re.findall(r"\n\n([^#\n][^\n]+(?:\n[^#\n][^\n]+)*)", markdown)
        if paragraphs:
            summary = paragraphs[0].strip()

    if not summary:
        raise OutputContractError("LLM response missing summary content.")

    # Extract key_points from ## 核心要点 section
    key_points = _extract_key_points(markdown)

    # Extract detailed_content from ## 详细内容 section
    detailed_content = _extract_detailed_content(markdown)

    # Extract tags from ## 标签 section
    tags = _extract_tags(markdown)

    # Extract transcript_excerpt from ## 原文摘录 or > blockquote
    transcript_excerpt = _extract_transcript_excerpt(markdown)
    if not transcript_excerpt:
        transcript_excerpt = source_text[:500].strip()

    return ResponseContent(
        title=title,
        summary=summary.strip(),
        key_points=key_points if key_points else ["Key point extraction failed"],
        detailed_content=detailed_content,
        tags=tags,
        transcript_excerpt=transcript_excerpt.strip(),
        markdown=markdown,
    )


def _parse_json_legacy(
    payload: dict[str, Any], *, source_text: str, raw_markdown: str
) -> ResponseContent:
    """Parse legacy JSON format for backward compatibility."""
    title = payload.get("title")
    summary = payload.get("summary")
    key_points = payload.get("key_points")
    detailed_content = payload.get("detailed_content")
    tags = payload.get("tags")
    transcript_excerpt = payload.get("transcript_excerpt")

    if not isinstance(title, str) or not title.strip():
        title = "视频内容总结"
    if not isinstance(summary, str) or not summary.strip():
        raise OutputContractError("LLM JSON missing non-empty summary.")
    if not isinstance(key_points, list) or not 3 <= len(key_points) <= 5:
        raise OutputContractError("LLM JSON key_points must contain 3 to 5 items.")
    if not all(isinstance(item, str) and item.strip() for item in key_points):
        raise OutputContractError("LLM JSON key_points must be non-empty strings.")

    normalized_tags = tags if isinstance(tags, list) else []
    if not all(isinstance(item, str) and item.strip() for item in normalized_tags):
        raise OutputContractError("LLM JSON tags must be strings.")

    if not isinstance(transcript_excerpt, str) or not transcript_excerpt.strip():
        transcript_excerpt = source_text[:500].strip()

    # Parse detailed_content
    normalized_detailed_content: list[dict[str, str]] = []
    if isinstance(detailed_content, list):
        for section in detailed_content:
            if isinstance(section, dict):
                section_title = str(section.get("section_title", "")).strip()
                content = str(section.get("content", "")).strip()
                if section_title and content:
                    normalized_detailed_content.append({
                        "section_title": section_title,
                        "content": content,
                    })

    # Truncate long Chinese summary for backward compatibility
    normalized_summary = summary.strip()
    # Detect if summary is mostly Chinese characters
    if len(normalized_summary) > 200:
        chinese_chars = sum(1 for c in normalized_summary if '\u4e00' <= c <= '\u9fff')
        if chinese_chars > len(normalized_summary) * 0.5:
            normalized_summary = normalized_summary[:200].rstrip()

    return ResponseContent(
        title=title.strip(),
        summary=normalized_summary,
        key_points=[item.strip() for item in key_points],
        detailed_content=normalized_detailed_content,
        tags=[item.strip() for item in normalized_tags],
        transcript_excerpt=transcript_excerpt.strip(),
        markdown=raw_markdown,
    )


def _extract_section_content(markdown: str, section_name: str) -> str:
    """Extract content from a ## section."""
    pattern = rf"##\s+{re.escape(section_name)}\s*\n\n(.+?)(?=\n##\s|\Z)"
    match = re.search(pattern, markdown, re.DOTALL)
    if match:
        return match.group(1).strip()
    return ""


def _extract_key_points(markdown: str) -> list[str]:
    """Extract key points from ## 核心要点 / ## 关键要点 / ## 要点 section.
    
    Supports multiple formats:
    - Numbered: 1. **Title**: explanation
    - Bullet: - **Title**: explanation  
    - Simple bullet: - point text
    """
    section = _extract_section_content(markdown, "核心要点")
    if not section:
        section = _extract_section_content(markdown, "关键要点")
    if not section:
        section = _extract_section_content(markdown, "要点")
    if not section:
        return []

    points = []
    for line in section.split("\n"):
        line = line.strip()
        if not line:
            continue
        # Match numbered format: 1. **Title**: explanation
        # Match bullet format: - **Title**: explanation
        match = re.match(r"^(?:\d+\.|-)\s+(.+)$", line)
        if match:
            point = match.group(1).strip()
            # Remove bold markers **
            point = re.sub(r"\*\*(.+?)\*\*", r"\1", point)
            points.append(point)
    return points


def _extract_detailed_content(markdown: str) -> list[dict[str, str]]:
    """Extract detailed sections from ## 详细内容 section."""
    section = _extract_section_content(markdown, "详细内容")
    if not section:
        return []

    sections = []
    # Match ### subsections
    subsection_pattern = r"###\s+(.+?)\n\n(.+?)(?=\n###\s+|\Z)"
    for match in re.finditer(subsection_pattern, section, re.DOTALL):
        section_title = match.group(1).strip()
        content = match.group(2).strip()
        if section_title and content:
            sections.append({"section_title": section_title, "content": content})

    return sections


def _extract_tags(markdown: str) -> list[str]:
    """Extract tags from ## 标签 section.
    
    Supports multiple formats:
    - Comma/顿号 separated: tag1、tag2、tag3
    - Bullet list: - tag1\n- tag2
    - Inline list: ['tag1', 'tag2']
    """
    section = _extract_section_content(markdown, "标签")
    if not section:
        return []

    # Try bullet list format first: - tag1\n- tag2
    bullet_tags = []
    for line in section.split("\n"):
        line = line.strip()
        match = re.match(r"^-\s+(.+)$", line)
        if match:
            bullet_tags.append(match.group(1).strip())
    if bullet_tags:
        return bullet_tags

    # Try Python list format: ['tag1', 'tag2']
    list_match = re.match(r"\[\s*'(.+?)'\s*\]", section, re.DOTALL)
    if list_match:
        inner = list_match.group(1)
        tags = re.split(r"'\s*,\s*'", inner)
        return [tag.strip() for tag in tags if tag.strip()]

    # Try comma/顿号 separated
    tags = re.split(r"[、,，\n]+", section)
    return [tag.strip() for tag in tags if tag.strip()]


def _extract_transcript_excerpt(markdown: str) -> str:
    """Extract transcript excerpt from ## 原文摘录 or blockquote."""
    section = _extract_section_content(markdown, "原文摘录")
    if section:
        # Remove > markers
        return re.sub(r"^>\s*", "", section, flags=re.MULTILINE).strip()

    # Fallback: find first blockquote
    blockquote_match = re.search(r"^>\s*(.+?)(?=\n\n|\Z)", markdown, re.MULTILINE | re.DOTALL)
    if blockquote_match:
        return blockquote_match.group(1).strip()

    return ""


def _chat_completions_url(api_base: str) -> str:
    normalized = api_base.rstrip("/") + "/"
    if normalized.endswith("chat/completions/"):
        return normalized[:-1]
    return urljoin(normalized, "chat/completions")


def _read_http_error_detail(exc: HTTPError) -> str:
    try:
        raw = exc.read().decode("utf-8", errors="replace").strip()
    except Exception:
        return ""
    if not raw:
        return ""
    return raw[:300]


def _looks_llm_safety_refusal(detail: str) -> bool:
    normalized = detail.lower()
    markers = (
        "new_sensitive",
        "sensitive",
        "safety",
        "policy",
        "refused",
        "content_filter",
    )
    return any(marker in normalized for marker in markers)


def _render_user_prompt(
    template: str,
    *,
    output_language: str,
    language_instruction: str,
    transcript: str,
    video_url: str = "",
    video_duration: str = "",
    video_strategy: str = "",
    video_language: str = "",
) -> str:
    placeholders = set(re.findall(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", template))
    unsupported = placeholders - PROMPT_TEMPLATE_KEYS
    if unsupported:
        allowed = ", ".join(sorted(PROMPT_TEMPLATE_KEYS))
        raise OutputContractError(
            f"LLM prompt template contains an unsupported placeholder. "
            f"Allowed placeholders: {allowed}."
        )
    return (
        template.replace("{output_language}", output_language)
        .replace("{language_instruction}", language_instruction)
        .replace("{transcript}", transcript)
        .replace("{video_url}", video_url)
        .replace("{video_duration}", video_duration)
        .replace("{video_strategy}", video_strategy)
        .replace("{video_language}", video_language)
    )
