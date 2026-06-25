# Video-Agent-Skill · Video Content Summarizer

<p align="center">
  <a href="README.md">中文</a> | <a href="README_EN.md">English</a> | <a href="README_VI.md">Tiếng Việt</a>
</p>

<div align="center">

**Give your AI Agent the ability to "watch" videos**

Let your LLM Agent directly "understand" any video link — extracts subtitles in seconds, falls back to local ASR when needed, and outputs structured summaries.

</div>

---

## What Is This?

Ever asked your AI assistant to summarize a YouTube or Bilibili video, only to get "I can't access video links"?

**Video-Agent-Skill** fixes that. It's a command-line tool that acts as a "video reader" for AI Agents — you feed it a video URL, it turns the content into a structured text summary, and your Agent can process videos just like regular text.

### Why Do You Need It?

| Pain Point | Video-Agent-Skill Solution |
|-----------|---------------------------|
| **Cloud APIs charge per minute and require uploading videos** | Local processing, zero API cost (except LLM summary), audio never uploaded to third parties |
| **Browser extensions can't be called by Agents** | Pure CLI tool, Agent calls directly, outputs standard JSON |
| **Downloading entire videos is slow and huge** | Smart fallback: grab subtitles first (seconds), only download low-bitrate audio if no subtitles |
| **Not enough GPU VRAM for long videos** | Automatic VAD slicing, 30-second chunks, run 1-hour videos on 4GB VRAM |
| **Different platforms need different network access** | Proxy routing, match by domain, works with YouTube, Bilibili, etc. |

### How Does It Work?

```
Video URL ──→ Subtitle-first extraction (seconds)
               │
               ├─ Has subtitles ──→ Download subtitle text ──→ LLM summary ──→ JSON/Markdown
               │
               └─ No subtitles  ──→ Download low-bitrate audio ──→ VAD slicing ──→ Local ASR ──→ LLM summary
```

1. **Subtitle-first**: Try to grab platform subtitles (uploader-edited or auto-generated). If available, use the subtitle path for second-level response.
2. **ASR fallback**: No subtitles? Download audio and transcribe locally with Alibaba SenseVoice — no cost, no privacy leak.
3. **LLM summary**: Feed the transcript to an OpenAI-compatible LLM (e.g., MiniMax, Ollama) to extract title, summary, key points, detailed content, and tags.
4. **Standard output**: Results as JSON (for Agents) or Markdown (for humans). All logs go to stderr, never polluting stdout.

### Who Uses It?

- **Agent developers**: Integrate into Dify, FastGPT, Claude Code, and other orchestration frameworks
- **Power users**: Run from terminal for quick video summaries
- **System maintainers**: Configure proxy routing, deploy Docker, tune LLM parameters

---

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
src/video_agent_skill/core/extractor.py Metadata probing, subtitle extraction, audio download
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

## Installation & Configuration

### Prerequisites

Ensure the following dependencies are ready before use:

| Dependency | Purpose | Required | Installation |
|-----------|---------|----------|-------------|
| **Python 3.10+** | Runtime | Required | System or conda |
| **FFmpeg** | Audio format conversion (subtitle path doesn't need it, ASR path does) | ASR path | Add to system PATH |
| **yt-dlp** | Video metadata probing, subtitle/audio download | Required (installed with pip package) | `pip install yt-dlp` or with this package |
| **PySocks** | SOCKS5 proxy support (needed for YouTube access) | Depends on proxy | `pip install PySocks` or with this package |
| **FunASR + PyTorch** | Local ASR engine (SenseVoice model) | ASR path | See "ASR Environment Setup" below |
| **LLM API Key** | LLM summarization | Summary feature | See "LLM Configuration" below |

> **Note**: If the video has subtitles, the subtitle path doesn't need ASR — it returns in seconds. Only videos without subtitles fall back to the ASR path, which requires FunASR + PyTorch.

### ASR Environment Setup (for videos without subtitles)

ASR transcription uses Alibaba's **SenseVoiceSmall** model via the **FunASR** framework, which depends on **PyTorch**. These dependencies are large (with CUDA support), so a dedicated conda environment is recommended:

```powershell
# 1. Create a dedicated conda environment
conda create -n milvus python=3.10
conda activate milvus

# 2. Install PyTorch (choose based on your GPU)
# With NVIDIA GPU (CUDA):
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
# Without GPU (CPU mode, slower):
pip install torch torchaudio

# 3. Install FunASR
pip install funasr

# 4. Install FFmpeg and add to PATH
# Windows: Download from https://ffmpeg.org/download.html, add bin to PATH
# Linux:   sudo apt install ffmpeg
# Mac:     brew install ffmpeg

# 5. Install video-agent-skill
pip install dist/video_agent_skill-*.whl

# 6. Verify ASR environment
video-agent --doctor
# Output should show asr device as cuda or cpu, funasr as installed
```

**SenseVoice Source Directory (optional)**:

By default, FunASR auto-downloads the `iic/SenseVoiceSmall` model from ModelScope. If you have a local SenseVoice source checkout (containing `model.py`), specify it in config.yaml:

```yaml
ai:
  asr:
    source_dir: "G:/Projects/Sources/SenseVoice"  # Directory containing model.py
```

Or via CLI parameter:

```powershell
video-agent -u "..." --sensevoice-source-dir "G:/Projects/Sources/SenseVoice"
```

**ASR Device Selection**:

```yaml
ai:
  asr:
    device: "auto"  # Auto-detect: cuda -> mps -> cpu
    # device: "cuda"  # Force GPU
    # device: "cpu"   # Force CPU
```

- `auto`: Auto-detect, priority `cuda` (NVIDIA GPU) -> `mps` (Apple Silicon) -> `cpu`
- `cuda`: Force GPU, error if unavailable
- `cpu`: Force CPU, slower but maximum compatibility

### LLM Configuration (for summary feature)

LLM summarization uses an OpenAI-compatible interface, defaulting to MiniMax. You need an API key:

1. **Get an API key**: Register at [MiniMax Open Platform](https://www.minimaxi.com/)
2. **Fill in config**: Edit `ai.llm.api_key` in config.yaml

```yaml
ai:
  llm:
    api_base: "https://api.minimaxi.com/v1"  # OpenAI-compatible endpoint
    model_name: "MiniMax-M2.7"               # Model name
    api_key: "your-api-key-here"             # Your API key
    timeout_seconds: 60
```

Or pass via CLI parameter (overrides config.yaml):

```powershell
video-agent -u "..." --llm-api-key "your-api-key"
```

**Using other LLMs** (e.g., local Ollama):

```yaml
ai:
  llm:
    api_base: "http://127.0.0.1:11434/v1"  # Ollama local address
    model_name: "qwen2.5"                   # Local model name
    api_key: "ollama"                       # Ollama doesn't need a real key, use any value
```

### Installation Methods

#### Method 1: pip Install Wheel (Recommended)

```powershell
pip install dist/video_agent_skill-*.whl
video-agent --version
```

#### Method 2: Global Install With pipx

```powershell
pipx install .
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

#### Method 3: Run From Source With uv (development)

```powershell
uv run video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

#### Method 4: Docker

```powershell
docker build -t video-agent-skill .
docker run --rm video-agent-skill -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

> **Note**: Dockerfile has been written but not yet built or verified in a real environment.

### First-Time Setup Checklist

After installation, verify with these steps:

```powershell
# 1. Show version
video-agent --version

# 2. Environment diagnostics (checks yt-dlp, FFmpeg, ASR, LLM config)
video-agent --doctor

# 3. Generate config and prompts in current directory (for easy editing)
video-agent --setup

# 4. Edit ./config.yaml — fill in API Key, proxy, ASR paths, etc.

# 5. Test subtitle path (captioned YouTube video, requires proxy)
video-agent -u "https://www.youtube.com/watch?v=KGUXXUCV6S4" --lang en --proxy "http://127.0.0.1:7890" --transcript-only

# 6. Test full pipeline (LLM summary)
video-agent -u "https://www.youtube.com/watch?v=KGUXXUCV6S4" --lang zh --proxy "http://127.0.0.1:7890" --output-format markdown --output-file summary.md
```

### Wheel Release Rules

- `pyproject.toml` must define project name, version, dependencies, and the `video-agent` console entry point.
- Run contract tests before every release to keep `stdout` as pure JSON.
- `config.yaml` is packaged into the wheel but must be an empty template (`api_key: ""`); never include real credentials.
- Do not commit `dist/` artifacts to source control unless attached to an official Release.
- Use semantic versioning: `MAJOR.MINOR.PATCH`.

## Configuration

### Config Loading Rules

Config is loaded by priority (higher overrides lower):

| Priority | Source | Description |
|----------|--------|-------------|
| 1 | CLI parameters | `--proxy`, `--llm-api-key`, etc. override fields |
| 2 | Current directory `./config.yaml` | Project-level override, generate with `--setup` |
| 3 | Bundled `config.yaml` | Default (in site-packages, removed by pip uninstall) |

Prompt templates follow the same pattern: `./prompts/` in the current directory takes priority over bundled `prompts/`.

### Generate Config in Current Directory

Use `--setup` to generate editable config and prompts in the current working directory:

```powershell
# Generate config.yaml and prompts/ in current directory
video-agent --setup

# Overwrite existing files
video-agent --setup --overwrite
```

Edit the generated `config.yaml` directly — it doesn't affect the bundled default.

### Config File Location

- **Current directory config**: `./config.yaml` (generated by `--setup`, takes priority)
- **Bundled default config**: `site-packages/video_agent_skill/config.yaml` (installed with package)

Find the bundled config path:

```powershell
python -c "import video_agent_skill; from pathlib import Path; print(Path(video_agent_skill.__file__).parent / 'config.yaml')"
```

### Config Example

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
    device: "auto"                          # auto/cuda/mps/cpu
    model: "iic/SenseVoiceSmall"            # FunASR model name
    source_dir: "G:/Projects/Sources/SenseVoice"  # Local SenseVoice source dir (optional)
  llm:
    api_base: "https://api.minimaxi.com/v1"  # OpenAI-compatible endpoint
    model_name: "MiniMax-M2.7"              # Model name
    api_key: ""                             # Fill in your API Key
    timeout_seconds: 60
    system_prompt: ""                       # Leave empty to use bundled default
    user_prompt_template: ""                # Leave empty to use bundled default

output:
  format: "markdown"  # json or markdown
  file: ""
  batch_separator: "---"
```

### CLI Parameter Overrides

```powershell
# Override proxy
video-agent -u "..." --lang zh --proxy "http://127.0.0.1:7890"

# Override API key
video-agent -u "..." --lang zh --llm-api-key "your-key"

# Override output format
video-agent -u "..." --lang zh --output-format json

# Override ASR device
video-agent -u "..." --lang zh --asr-device cuda
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
