# Video-Agent-Skill

`Video-Agent-Skill` is a headless CLI component for AI Agent workflows. It accepts a streaming video URL, extracts existing subtitles first, falls back to local ASR when subtitles are unavailable, and returns structured JSON or human-readable Markdown that an Agent can parse reliably.

> Current version v1.0.0: Subtitle-first extraction, audio fallback download, SenseVoice/FunASR ASR wrapping, OpenAI-compatible LLM summarization (Markdown/JSON dual format), prompt file management, environment diagnostics, Bilibili danmaku analysis, result caching, progress reporting, batch processing, and Wheel packaging are all ready. 58 unit tests pass, ruff linting passes, wheel builds successfully. Bilibili HTTP 412 anti-crawler issue has been fixed.

## Core Capabilities

- **Subtitle-first extraction**: Prefer uploaded or platform-generated subtitles to avoid unnecessary downloads and inference.
- **Local ASR fallback**: Download low-bitrate audio and transcribe it locally with `SenseVoiceSmall` when subtitles are missing.
- **Bilibili danmaku analysis**: Extract and analyze bullet comments to gain insight into audience sentiment, hot topics, and viewer profiles.
- **Dual format output**: Supports `json` (Agent parsing) and `markdown` (human reading) via `--output-format` or `config.yaml`.
- **Agent-grade I/O contract**: Logs, progress bars, and third-party library output go to `stderr`; `stdout` contains only one JSON or Markdown object.
- **Proxy routing**: Match proxy rules by domain for platforms such as YouTube, Bilibili, and Douyin.
- **Standard delivery**: Supports `uv` development, `pip`/`pipx` installation, and Wheel offline distribution.

## Directory Structure

```text
src/video_agent_skill/cli.py            CLI entry, global error handling, stdout/stderr isolation
src/video_agent_skill/core/extractor.py Metadata probing, subtitle extraction, audio download, Bilibili 412 bypass
src/video_agent_skill/core/transcriber.py VAD slicing, local ASR inference, transcript cleanup
src/video_agent_skill/core/summarizer.py LLM summary generation, Markdown/JSON dual-format parsing
src/video_agent_skill/core/danmaku.py   Bilibili danmaku extraction and analysis
src/video_agent_skill/utils/config.py   config.yaml loading, proxy routing, CLI parameter overrides
src/video_agent_skill/utils/cache.py    Result caching
src/video_agent_skill/utils/progress.py Progress reporting
src/video_agent_skill/utils/retry.py    Error retry
src/video_agent_skill/utils/logging.py  Tiered logging
src/video_agent_skill/prompts/          Default prompt templates (installed with package)
tests/                                  Unit, integration, and contract tests
docs/                                   Product, requirements, architecture, design, and planning docs
```

## Quick Start

```powershell
# Show version
video-agent --version

# Environment diagnostics (no URL required)
video-agent --doctor

# Basic usage (JSON output to stdout)
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh

# Markdown output to file
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --output-format markdown --output-file summary.md
```

## Command-Line Parameters

| Parameter | Required | Description |
|-----------|----------|-------------|
| `-u, --url` | Yes | Target video URL |
| `-l, --lang` | No | Preferred subtitle language, default `zh` |
| `--proxy` | No | Force proxy for this run |
| `--keep-temp` | No | Keep temporary files for debugging |
| `--transcript-only` | No | Return transcript only, skip LLM |
| `--output-format` | No | `json` (default) or `markdown` |
| `--output-file` | No | Output file path, default stdout |
| `--llm-api-key` | No | LLM API Key |
| `--llm-api-base` | No | LLM API Base URL |
| `--llm-model` | No | LLM model name |
| `--llm-system-prompt-file` | No | System prompt file path |
| `--llm-user-prompt-file` | No | User prompt file path |
| `--asr-device` | No | ASR device: `auto`/`cuda`/`mps`/`cpu` |
| `--sensevoice-source-dir` | No | SenseVoice source directory |
| `--include-danmaku` | No | Enable Bilibili danmaku analysis |
| `--danmaku-prompt-file` | No | Danmaku analysis prompt file |
| `--danmaku-output` | No | Danmaku analysis separate output file |
| `--batch` | No | Batch process URLs from file |
| `--no-cache` | No | Disable result caching for this run |
| `--clear-cache` | No | Clear all cached entries and exit |
| `--no-progress-bar` | No | Disable visual progress bar |
| `--doctor` | No | Environment diagnostics, no URL required |
| `--version, -V` | No | Show version |
| `--prompt-info` | No | Show bundled default prompt info |
| `--init-prompts [DIR]` | No | Copy default prompts to local directory |
| `--init-config [DIR]` | No | Copy config template to directory |
| `--config` | No | Specify config.yaml path, default reads bundled |

## Installation

### Method 1: Run From Source With uv

```powershell
uv run video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

### Method 2: Global Install With pipx

```powershell
pipx install .
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

### Method 3: Wheel Build And pip Install

```powershell
uv build --wheel
pip install dist/video_agent_skill-*.whl
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

Wheel release rules (see `AGENTS.md`):

- `pyproject.toml` must define project name, version, dependencies, and the `video-agent` console entry point.
- Run contract tests before every release to keep `stdout` as pure JSON.
- `config.yaml` is packaged into the wheel but must be an empty template (`api_key: ""`); never include real credentials.
- Do not commit `dist/` artifacts to source control unless attached to an official Release.
- Use semantic versioning: `MAJOR.MINOR.PATCH`.

### Method 4: Docker

```powershell
docker build -t video-agent-skill .
docker run --rm video-agent-skill -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

> **Note**: Dockerfile has been written but not yet built or verified in a real environment.

## Configuration

### Config Loading Rules

**Config is loaded only from the bundled `config.yaml`; CLI parameters override individual fields.**

- Config file location: `site-packages/video_agent_skill/config.yaml` (installed with package, removed by pip uninstall)
- CLI parameters (e.g., `--proxy`, `--llm-api-key`) override corresponding fields in config.yaml
- No environment variables, no current-directory overrides

### Config Example

Edit `site-packages/video_agent_skill/config.yaml` after installation:

```yaml
system:
  temp_dir: ""
  auto_cleanup: true

network:
  default_proxy: ""
  rules:
    - domains: ["youtube.com", "youtu.be"]
      proxy: "http://127.0.0.1:7890"
    - domains: ["bilibili.com", "douyin.com"]
      proxy: "direct"

ai:
  asr:
    device: "auto"
    model: "iic/SenseVoiceSmall"
    source_dir: "G:/Projects/Sources/SenseVoice"
  llm:
    api_base: "https://api.minimaxi.com/v1"
    model_name: "MiniMax-M2.7"
    api_key: ""  # Fill in your API Key here
    timeout_seconds: 60
    system_prompt: ""
    user_prompt_template: ""

output:
  format: "markdown"  # json or markdown
  file: ""
  batch_separator: "---"
```

### CLI Parameter Overrides

```powershell
# Override proxy
video-agent -u "..." --lang zh --proxy "http://127.0.0.1:8964"

# Override API key
video-agent -u "..." --lang zh --llm-api-key "your-key"

# Override output format
video-agent -u "..." --lang zh --output-format json
```

## Prompt Templates

Default prompt files are installed at `site-packages/video_agent_skill/prompts/`:

| File | Purpose |
|------|---------|
| `default-system.txt` | System prompt, defines LLM role |
| `default-video-summary.txt` | Video summary prompt with field specs and output examples |
| `default-danmaku.txt` | Danmaku analysis prompt (Bilibili only) |

`default-video-summary.txt` supports these placeholders (auto-replaced by code):

| Placeholder | Replaced with |
|-------------|---------------|
| `{output_language}` | Output language (e.g., `Simplified Chinese`) |
| `{language_instruction}` | Language instruction |
| `{transcript}` | Video transcript text |
| `{video_url}` | Video URL |
| `{video_duration}` | Video duration (e.g., `1123 seconds`) |
| `{video_strategy}` | Processing strategy (`subtitle` or `asr`) |
| `{video_language}` | Video language |

Custom prompts:

```powershell
# Show bundled prompt info
video-agent --prompt-info

# Copy default prompts to local directory
video-agent --init-prompts ./my-prompts

# Use custom prompt files
video-agent -u "..." --lang zh \
  --llm-system-prompt-file "./my-prompts/default-system.txt" \
  --llm-user-prompt-file "./my-prompts/default-video-summary.txt"
```

## Output Contract

### JSON Format (Default)

```json
{
  "status": "success",
  "meta": {
    "url": "https://www.youtube.com/watch?v=xxxx",
    "strategy_used": "subtitle",
    "language": "zh",
    "duration_seconds": 860
  },
  "content": {
    "title": "Specific video topic title",
    "summary": "Detailed summary paragraph...",
    "key_points": ["Key point 1...", "Key point 2..."],
    "detailed_content": [
      {"section_title": "Section heading", "content": "Detailed content..."}
    ],
    "tags": ["AI", "Agent", "video summary"],
    "transcript_excerpt": "Transcript excerpt...",
    "markdown": "Full Markdown content (when output_format=markdown)"
  },
  "error": null
}
```

### Markdown Format

Use `--output-format markdown` for human-readable structured Markdown with: title, video info, summary, key points, detailed content, tags, transcript excerpt.

Failed runs return JSON with a non-zero exit code:

```json
{
  "status": "error",
  "meta": {"url": "...", "strategy_used": "none", "language": "zh"},
  "content": null,
  "error": {"code": "AUTH_REQUIRED_ERROR", "message": "The target video requires login or paid access"}
}
```

## Development Verification

```powershell
uv run pytest tests/                                    # Unit tests
uv run ruff check .                                     # Linting
uv build --wheel                                        # Build wheel
video-agent --version                                   # Show version
video-agent --doctor                                    # Environment diagnostics
video-agent -u "<URL>" --lang zh --transcript-only      # Transcript only
video-agent -u "<URL>" --lang zh --output-format markdown --output-file summary.md
```

Acceptance checkpoints:

- Captioned videos use the `subtitle` path and return within 5 seconds.
- Videos without captions use the `asr` path without GPU OOM on long audio.
- Bilibili `danmaku` is not treated as transcript subtitles; those videos fall back to ASR.
- Bilibili HTTP 412 anti-crawler issue has been fixed via dynamic buvid3/buvid4 cookie + Origin header.
- Redirected stdout can be parsed directly by `json.loads`.
- Network, authentication, and LLM timeout failures return standard error JSON.
- Temporary UUID workspaces are removed by default after each run.

## Documentation Map

| Document | Description |
|----------|-------------|
| `docs/工作进展记录.md` | Ongoing log for design, development, testing, and decisions |
| `docs/requirements.md` | Testable software requirements |
| `docs/技术架构设计说明书.md` | Technology choices, logical architecture, and deployment design |
| `docs/概要设计说明书.md` | Module boundaries, configuration structure, and data protocol |
| `docs/详细设计说明书.md` | Module-level implementation details, error codes, and cleanup design |
| `docs/验收测试计划.md` | MVP test scope, acceptance cases, JSON assertions, and error-code baseline |
| `docs/用户使用说明书.md` | Detailed user manual, parameter reference, and FAQ |
| `config.example.yaml` | Configuration template with comments |
| `AGENTS.md` | Agent development guide and release packaging rules |
