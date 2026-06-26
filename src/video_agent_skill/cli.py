from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from video_agent_skill.contracts import (
    ResponseContent,
    ResponseMeta,
    error_response,
    success_response,
)
from video_agent_skill.core.extractor import extract_text_from_url
from video_agent_skill.core.summarizer import summarize_text
from video_agent_skill.doctor import run_doctor
from video_agent_skill.errors import InvalidArgumentError, VideoAgentError
from video_agent_skill.prompt_files import copy_default_prompts, get_prompt_info
from video_agent_skill.utils.config import (
    CliOverrides,
    load_config,
    resolve_asr_config,
    resolve_asr_device_config,
    resolve_llm_config,
    resolve_proxy,
)
from video_agent_skill.utils.logging import error as log_error
from video_agent_skill.utils.logging import info
from video_agent_skill.utils.logging import success as log_success
from video_agent_skill.utils.logging import warning


def app() -> int:
    return main()


def main(argv: Sequence[str] | None = None) -> int:
    sys.stdout = sys.stderr
    args_list = list(sys.argv[1:] if argv is None else argv)
    if any(item in {"-h", "--help"} for item in args_list):
        _build_parser().print_help(sys.stderr)
        return 0
    if any(item in {"-V", "--version"} for item in args_list):
        from video_agent_skill import __version__
        sys.stderr.write(f"video-agent {__version__}\n")
        return 0

    url = _extract_url_for_error(args_list)
    language = _extract_language_for_error(args_list)

    try:
        args = _parse_args(args_list)
        if args.prompt_info:
            _render_agent_output(get_prompt_info())
            return 0
        if args.init_prompts is not None:
            _render_agent_output(
                copy_default_prompts(
                    args.init_prompts,
                    overwrite=args.overwrite_prompts,
                )
            )
            return 0
        if args.init_config is not None:
            from video_agent_skill.config_init import init_config
            target_dir = args.init_config if args.init_config else None
            _render_agent_output(
                init_config(
                    target_dir,
                    overwrite=args.overwrite,
                    include_prompts=True,
                )
            )
            return 0
        if args.setup:
            from video_agent_skill.config_init import init_config
            _render_agent_output(
                init_config(
                    Path.cwd(),
                    overwrite=args.overwrite,
                    include_prompts=True,
                )
            )
            return 0

        config = load_config(args.config)
        overrides = CliOverrides(
            proxy=args.proxy,
            llm_api_key=args.llm_api_key,
            llm_api_base=args.llm_api_base,
            llm_model=args.llm_model,
            llm_system_prompt=args.llm_system_prompt,
            llm_system_prompt_file=args.llm_system_prompt_file,
            llm_user_prompt_template=args.llm_user_prompt_template,
            llm_user_prompt_file=args.llm_user_prompt_file,
            asr_device=args.asr_device,
            sensevoice_source_dir=args.sensevoice_source_dir,
        )
        proxy = resolve_proxy(args.url, config, args.proxy)
        llm = resolve_llm_config(config, overrides)
        asr = resolve_asr_config(config, overrides)
        resolve_asr_device_config(config, overrides)

        # Resolve output settings: CLI args > config.yaml > defaults
        output_format = args.output_format or config.output.format or "json"
        output_file = args.output_file or config.output.file or None

        if args.doctor:
            _render_agent_output(run_doctor(config=config, asr=asr, llm=llm), pretty=True)
            return 0

        # Clear cache and exit
        if args.clear_cache:
            from video_agent_skill.utils.cache import clear_cache, get_cache_stats
            stats_before = get_cache_stats()
            removed = clear_cache()
            stats_after = get_cache_stats()
            _render_agent_output({
                "status": "success",
                "message": f"Cache cleared: {removed} files removed",
                "before": stats_before,
                "after": stats_after,
            })
            return 0

        # Batch mode: process URLs from file
        if args.batch:
            return _run_batch(
                batch_file=args.batch,
                lang=args.lang,
                proxy=proxy,
                llm=llm,
                asr=asr,
                config=config,
                transcript_only=args.transcript_only,
                include_danmaku=args.include_danmaku,
                danmaku_prompt_file=args.danmaku_prompt_file,
                output_format=output_format,
                output_file=output_file,
                use_cache=not args.no_cache,
            )

        if not args.url:
            raise InvalidArgumentError("Missing required argument: -u/--url.")

        return _run_single(
            url=args.url,
            lang=args.lang,
            proxy=proxy,
            llm=llm,
            asr=asr,
            config=config,
            transcript_only=args.transcript_only,
            include_danmaku=args.include_danmaku,
            danmaku_prompt_file=args.danmaku_prompt_file,
            output_format=output_format,
            output_file=output_file,
            use_cache=not args.no_cache,
            progress_bar=not args.no_progress_bar,
        )
    except VideoAgentError as exc:
        response = error_response(
            url=url,
            language=language,
            code=exc.code,
            message=str(exc),
        )
        _render_agent_output(
            response.to_dict(),
            output_format=locals().get("args").output_format if locals().get("args") else "json",
            output_file=locals().get("args").output_file if locals().get("args") else None,
        )
        log_error(f"Processing failed: {exc.code} - {exc}")
        return exc.exit_code
    except Exception as exc:  # pragma: no cover - defensive outer contract.
        response = error_response(
            url=url,
            language=language,
            code="UNEXPECTED_ERROR",
            message=f"Unexpected runtime error: {exc.__class__.__name__}",
        )
        _render_agent_output(
            response.to_dict(),
            output_format=locals().get("args").output_format if locals().get("args") else "json",
            output_file=locals().get("args").output_file if locals().get("args") else None,
        )
        log_error(f"Processing failed: UNEXPECTED_ERROR - {exc.__class__.__name__}: {exc}")
        return 1


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = _build_parser()

    try:
        return parser.parse_args(list(argv))
    except argparse.ArgumentError as exc:
        raise InvalidArgumentError(str(exc)) from exc
    except SystemExit as exc:
        message = f"Invalid CLI arguments. argparse exited with {exc.code}."
        raise InvalidArgumentError(message) from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="video-agent",
        description=(
            "Parse a video URL and return an Agent-compatible JSON or Markdown summary.\n\n"
            "Subtitle-first extraction: downloads subtitles if available, "
            "falls back to audio download + local ASR (SenseVoice).\n"
            "Results are sent to an LLM for structured summarization.\n\n"
            "Output goes to stdout (or --output-file) as a single JSON object by default. "
            "All logs, progress, and diagnostics go to stderr."
        ),
        add_help=True,
        exit_on_error=False,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  # Basic usage (JSON output)\n"
            "  video-agent -u \"https://www.youtube.com/watch?v=xxxx\" --lang zh\n\n"
            "  # Markdown output to file\n"
            "  video-agent -u \"https://www.youtube.com/watch?v=xxxx\" --lang zh \\\n"
            "    --output-format markdown --output-file summary.md\n\n"
            "  # Transcript only (no LLM, faster)\n"
            "  video-agent -u \"https://www.youtube.com/watch?v=xxxx\" --lang en \\\n"
            "    --transcript-only\n\n"
            "  # Batch processing from file\n"
            "  video-agent --batch urls.txt --lang zh --output-file results.json\n\n"
            "  # Environment diagnostics\n"
            "  video-agent --doctor\n\n"
            "Configuration priority: CLI args > Environment variables > config.yaml > Defaults\n"
            "Log level: set VIDEO_AGENT_LOG_LEVEL=DEBUG/INFO/WARNING/ERROR\n"
            "Cache: set VIDEO_AGENT_CACHE_DIR and VIDEO_AGENT_CACHE_TTL"
        ),
    )
    parser.add_argument("-u", "--url", default="", help="Target video URL.")
    parser.add_argument(
        "-V", "--version", action="store_true",
        help="Show the installed video-agent version and exit.",
    )
    parser.add_argument(
        "--doctor",
        action="store_true",
        help="Run environment diagnostics as JSON (checks yt-dlp, FFmpeg, ASR, LLM).",
    )
    parser.add_argument(
        "-l", "--lang", default="zh",
        help=(
            "Preferred subtitle language and LLM output language. "
            "Examples: zh (Simplified Chinese), zh-Hant (Traditional Chinese), "
            "en (English), ja (Japanese), ko (Korean), vi (Vietnamese), "
            "fr (French), de (German), es (Spanish), pt (Portuguese), "
            "ru (Russian), th (Thai), ar (Arabic), it (Italian). "
            "Default: zh."
        ),
    )
    parser.add_argument(
        "--proxy", default=None,
        help="Force a proxy for this run (e.g., socks5://127.0.0.1:7890).",
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="Keep temporary media files (audio, subtitles) for debugging.",
    )
    parser.add_argument(
        "--transcript-only", action="store_true",
        help="Return extracted transcript excerpt without calling LLM summarizer.",
    )
    parser.add_argument(
        "--prompt-info", action="store_true",
        help="Output JSON describing installed default prompt files. No URL required.",
    )
    parser.add_argument(
        "--init-prompts", nargs="?", const="prompts", default=None, metavar="DIR",
        help="Copy bundled default prompt files to DIR for editing. Default: ./prompts.",
    )
    parser.add_argument(
        "--overwrite-prompts", action="store_true",
        help="Allow --init-prompts to overwrite existing prompt files.",
    )
    parser.add_argument(
        "--config", default=None,
        help=(
            "Path to config.yaml. If omitted, searches: ./config.yaml (cwd) "
            "then the package directory config.yaml."
        ),
    )
    parser.add_argument(
        "--llm-api-key", default=None,
        help="Override LLM API key. Also set via VIDEO_AGENT_LLM_API_KEY env var.",
    )
    parser.add_argument(
        "--llm-api-base", default=None,
        help="Override LLM API base URL (default: https://api.minimaxi.com/v1).",
    )
    parser.add_argument(
        "--llm-model", default=None,
        help="Override LLM model name (default: MiniMax-M2.7).",
    )
    parser.add_argument(
        "--llm-system-prompt", default=None,
        help="Override LLM system prompt text directly.",
    )
    parser.add_argument(
        "--llm-system-prompt-file", default=None,
        help="Read the LLM system prompt from a UTF-8 text file.",
    )
    parser.add_argument(
        "--llm-user-prompt-template", default=None,
        help=(
            "Override LLM user prompt template. Supported placeholders: "
            "{output_language}, {language_instruction}, {transcript}."
        ),
    )
    parser.add_argument(
        "--llm-user-prompt-file", default=None,
        help="Read the LLM user prompt template from a UTF-8 text file.",
    )
    parser.add_argument(
        "--asr-device", default=None,
        help="Override ASR device: auto, cuda, mps, cpu. Default: auto.",
    )
    parser.add_argument(
        "--sensevoice-source-dir", default=None,
        help="Path to a local SenseVoice source checkout containing model.py.",
    )
    # Danmaku (bullet comment) options
    parser.add_argument(
        "--include-danmaku", action="store_true",
        help="Include danmaku (bullet comments) analysis. Only supported for Bilibili.",
    )
    parser.add_argument(
        "--danmaku-prompt-file", default=None,
        help="Path to a custom prompt file for danmaku analysis.",
    )
    parser.add_argument(
        "--danmaku-output", default=None,
        help="Path to write danmaku analysis as a separate Markdown file.",
    )
    parser.add_argument(
        "--output-format", default=None, choices=["json", "markdown"],
        help=(
            "Output format: json (Agent-compatible) or markdown (human-readable). "
            "If omitted, falls back to config.yaml output.format then 'json'."
        ),
    )
    parser.add_argument(
        "--no-progress-bar", action="store_true",
        help=(
            "Disable the visual progress bar. Use this when piping output "
            "or in non-interactive environments."
        ),
    )
    parser.add_argument(
        "--output-file", default=None,
        help="Path to write output file. If omitted, output goes to stdout.",
    )
    parser.add_argument(
        "--batch", default=None, metavar="FILE",
        help="Path to a file containing one URL per line for batch processing.",
    )
    parser.add_argument(
        "--no-cache", action="store_true",
        help="Disable result caching for this run. Overrides config and env settings.",
    )
    parser.add_argument(
        "--clear-cache", action="store_true",
        help="Clear all cached entries and exit. No URL required.",
    )
    parser.add_argument(
        "--init-config",
        nargs="?",
        const="",
        default=None,
        metavar="DIR",
        help=(
            "Initialize default config.yaml and prompt files for editing. "
            "If DIR is omitted, copies to the current working directory. "
            "Existing files are kept unless --overwrite is set."
        ),
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help=(
            "Generate config.yaml and prompts/ in the current working directory "
            "from package defaults. Existing files are kept unless --overwrite is set. "
            "When config.yaml exists in the current directory, it takes priority "
            "over the bundled package config."
        ),
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow --init-config or --setup to overwrite existing files.",
    )
    return parser


def _render_agent_output(
    data: dict[str, object],
    *,
    output_format: str = "json",
    output_file: str | None = None,
    pretty: bool = False,
) -> None:
    if output_format == "markdown":
        content = data.get("content", {})
        markdown = content.get("markdown", "") if isinstance(content, dict) else ""
        if not markdown:
            markdown = _generate_markdown(data)
        output = markdown
    else:
        if pretty:
            output = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            output = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    
    if output_file:
        from pathlib import Path
        Path(output_file).write_text(output, encoding="utf-8")
    else:
        if hasattr(sys.__stdout__, "reconfigure"):
            sys.__stdout__.reconfigure(encoding="utf-8")
        sys.__stdout__.write(output)
        sys.__stdout__.write("\n")
        sys.__stdout__.flush()


def _generate_markdown(data: dict[str, object]) -> str:
    """Generate markdown from JSON response data."""
    from datetime import datetime
    
    if data.get("status") != "success":
        error = data.get("error", {})
        return f"""# 处理失败

**错误码**: {error.get('code', 'UNKNOWN')}
**错误信息**: {error.get('message', 'Unknown error')}
"""

    meta = data["meta"]
    content = data["content"]

    duration = meta.get('duration_seconds')
    duration_str = f"{duration} 秒" if duration else "未知"

    md = f"""# {content['title']}

## 视频信息
- **URL**: {meta['url']}
- **处理策略**: {meta['strategy_used']}
- **语言**: {meta['language']}
- **时长**: {duration_str}
- **生成时间**: {datetime.now().isoformat()}

## 摘要

{content['summary']}

## 关键要点

"""

    for i, point in enumerate(content['key_points'], 1):
        md += f"{i}. {point}\n"

    md += "\n## 详细内容\n\n"
    for section in content.get('detailed_content', []):
        md += f"### {section['section_title']}\n\n{section['content']}\n\n"

    md += f"""## 标签

{'、'.join(content['tags'])}

## 转录片段

```
{content.get('transcript_excerpt', '')[:500]}...
```
"""

    return md


def _build_transcript_only_content(text: str) -> ResponseContent:
    excerpt = text.strip()
    if len(excerpt) > 2000:
        excerpt = excerpt[:2000].rstrip()
    return ResponseContent(
        title="视频内容总结",
        summary="Transcript extracted; LLM summarization was skipped.",
        key_points=[
            "Transcript-only mode was enabled.",
            "No LLM summary was generated.",
            "Use transcript_excerpt for the extracted text.",
        ],
        detailed_content=[],
        tags=["transcript-only"],
        transcript_excerpt=excerpt,
        markdown="",
    )


def _extract_url_for_error(argv: Sequence[str]) -> str:
    for index, item in enumerate(argv):
        if item in {"-u", "--url"} and index + 1 < len(argv):
            return argv[index + 1]
    return ""


def _extract_language_for_error(argv: Sequence[str]) -> str:
    for index, item in enumerate(argv):
        if item in {"-l", "--lang"} and index + 1 < len(argv):
            return argv[index + 1]
    return "zh"


def _run_single(
    *,
    url: str,
    lang: str,
    proxy: str | None,
    llm: Any,
    asr: Any,
    config: Any,
    transcript_only: bool,
    include_danmaku: bool,
    danmaku_prompt_file: str | None,
    output_format: str,
    output_file: str | None,
    use_cache: bool = True,
    progress_bar: bool = False,
) -> int:
    """Process a single video URL and return exit code."""
    from video_agent_skill.runtime import create_runtime_context as _create_runtime
    from video_agent_skill.utils.progress import ProgressTracker

    tracker = ProgressTracker(progress_bar=progress_bar)
    runtime = _create_runtime(
        temp_dir=config.system.temp_dir,
        keep_temp=False,  # Single run uses default cleanup
    )
    try:
        tracker.start_stage("extraction", f"Extracting text from {url}")
        extraction = extract_text_from_url(
            url,
            _language=lang,
            _proxy=proxy,
            _work_dir=runtime.work_dir,
            _asr=asr,
            _use_cache=use_cache,
            _timeout_seconds=config.network.timeout_seconds,
            _max_retries=config.network.max_retries,
        )
        tracker.complete(
            f"strategy={extraction.strategy_used}, "
            f"duration={extraction.duration_seconds}s, "
            f"transcript_length={len(extraction.text)} chars"
        )
    except Exception as exc:
        tracker.fail(f"Extraction failed: {exc}")
        raise
    finally:
        runtime.cleanup()

    # Danmaku extraction (optional, Bilibili only)
    danmaku_analysis = None
    danmaku_items = None
    representative = None
    danmaku_prompt_text = llm.danmaku_prompt if hasattr(llm, 'danmaku_prompt') else ""
    if include_danmaku:
        from video_agent_skill.core.danmaku import (
            analyze_danmaku,
            extract_danmaku,
            filter_representative_danmaku,
        )
        try:
            tracker.start_stage("danmaku", f"Extracting danmaku from {url}")
            danmaku_items = extract_danmaku(url, proxy=proxy)
            if danmaku_items:
                representative = filter_representative_danmaku(danmaku_items)
                tracker.complete(f"Extracted {len(danmaku_items)} danmaku items")
                if danmaku_prompt_file:
                    from pathlib import Path as _Path
                    try:
                        danmaku_prompt_text = _Path(danmaku_prompt_file).read_text(
                            encoding="utf-8"
                        )
                    except OSError:
                        warning(f"Failed to read danmaku prompt file: {danmaku_prompt_file}")
            else:
                tracker.complete("No danmaku found")
        except Exception as exc:
            tracker.fail(f"Danmaku extraction failed: {exc}")
            warning(f"Danmaku extraction failed: {exc}")

    if transcript_only:
        tracker.start_stage("summary", "Transcript-only mode, skipping LLM")
        content = _build_transcript_only_content(extraction.text)
        tracker.complete()
    else:
        tracker.start_stage("summary", "Generating LLM summary")
        content = summarize_text(
            extraction.text,
            _language=lang,
            _llm=llm,
            _duration_seconds=extraction.duration_seconds,
            _output_format=output_format,
            _video_url=url,
            _video_strategy=extraction.strategy_used,
        )
        tracker.complete()

    # If danmaku was extracted, analyze it now with video context
    if representative is not None and danmaku_items:
        try:
            tracker.start_stage("danmaku_analysis", "Analyzing danmaku with LLM")
            danmaku_analysis = analyze_danmaku(
                representative,
                video_title=getattr(content, 'title', ''),
                video_summary=getattr(content, 'summary', ''),
                _llm=llm,
                _prompt_template=danmaku_prompt_text,
            )
            if hasattr(content, 'markdown') and danmaku_analysis and danmaku_analysis.markdown:
                from dataclasses import replace
                new_markdown = content.markdown + "\n\n" + danmaku_analysis.markdown
                content = replace(content, markdown=new_markdown)
            tracker.complete()
        except Exception as exc:
            tracker.fail(f"Danmaku analysis error: {exc}")
            warning(f"Danmaku analysis error: {exc}")

    response = success_response(
        ResponseMeta(
            url=url,
            strategy_used=extraction.strategy_used,  # type: ignore[arg-type]
            language=lang,
            duration_seconds=extraction.duration_seconds,
        ),
        content,
    )
    _render_agent_output(
        response.to_dict(),
        output_format=output_format,
        output_file=output_file,
    )
    if output_file:
        log_success(
            f"Processing complete. Output written to {output_file} "
            f"(strategy={extraction.strategy_used}, format={output_format})"
        )
    else:
        log_success(
            f"Processing complete. Output sent to stdout "
            f"(strategy={extraction.strategy_used}, format={output_format})"
        )
    return 0


def _run_batch(
    *,
    batch_file: str,
    lang: str,
    proxy: str | None,
    llm: Any,
    asr: Any,
    config: Any,
    transcript_only: bool,
    include_danmaku: bool,
    danmaku_prompt_file: str | None,
    output_format: str,
    output_file: str | None,
    use_cache: bool = True,
) -> int:
    """Process multiple URLs from a batch file.

    Each URL is processed independently. Results are output as JSON Lines
    (one JSON object per line) to stdout or the output file.
    """
    from pathlib import Path

    batch_path = Path(batch_file)
    if not batch_path.exists():
        raise InvalidArgumentError(f"Batch file not found: {batch_file}")

    urls = [
        line.strip()
        for line in batch_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]

    if not urls:
        raise InvalidArgumentError(f"Batch file is empty or contains only comments: {batch_file}")

    results: list[dict[str, object]] = []
    exit_code = 0

    for i, url in enumerate(urls, 1):
        info(f"Processing {i}/{len(urls)}: {url}")
        try:
            code = _run_single(
                url=url,
                lang=lang,
                proxy=proxy,
                llm=llm,
                asr=asr,
                config=config,
                transcript_only=transcript_only,
                include_danmaku=include_danmaku,
                danmaku_prompt_file=danmaku_prompt_file,
                output_format="json",  # Batch internal format
                output_file=None,
                use_cache=use_cache,
            )
            if code != 0:
                exit_code = 1
        except VideoAgentError as exc:
            response = error_response(
                url=url,
                language=lang,
                code=exc.code,
                message=str(exc),
            )
            results.append(response.to_dict())
            exit_code = 1
        except Exception as exc:
            response = error_response(
                url=url,
                language=lang,
                code="UNEXPECTED_ERROR",
                message=f"Unexpected error: {exc.__class__.__name__}",
            )
            results.append(response.to_dict())
            exit_code = 1

    # Output all results
    if output_format == "markdown":
        # For markdown, concatenate all markdown outputs with separators
        def _fmt_result(r: dict[str, object]) -> str:
            if r.get("status") == "success":
                return _generate_markdown(r)
            url = r.get("meta", {}).get("url", "unknown")
            msg = r.get("error", {}).get("message", "Unknown")
            return f"# 处理失败\n\n**URL**: {url}\n**错误**: {msg}\n"

        output = "\n\n---\n\n".join(_fmt_result(r) for r in results)
    else:
        # JSON Lines format
        output = "\n".join(
            json.dumps(r, ensure_ascii=False, separators=(",", ":"))
            for r in results
        )

    if output_file:
        Path(output_file).write_text(output, encoding="utf-8")
    else:
        if hasattr(sys.__stdout__, "reconfigure"):
            sys.__stdout__.reconfigure(encoding="utf-8")
        sys.__stdout__.write(output)
        sys.__stdout__.write("\n")
        sys.__stdout__.flush()

    total = len(results)
    succeeded = sum(1 for r in results if r.get("status") == "success")
    failed = total - succeeded
    if exit_code == 0:
        log_success(
            f"Batch complete: {succeeded}/{total} succeeded. "
            f"Output: {output_file or 'stdout'}"
        )
    else:
        log_error(
            f"Batch complete: {succeeded}/{total} succeeded, {failed} failed. "
            f"Output: {output_file or 'stdout'}"
        )
    return exit_code
