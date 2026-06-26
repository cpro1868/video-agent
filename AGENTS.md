# Repository Guidelines

## Project Context

This repository is for `Video-Agent-Skill`, a headless Python CLI that lets AI Agents parse video URLs, extract subtitles first, fall back to local ASR, and return a single structured JSON object on `stdout`.

The project scaffold is initialized, and subtitle-first extraction, audio fallback download, OpenAI-compatible LLM summarization, and the SenseVoice/FunASR ASR wrapper have initial implementations. Real end-to-end validation is still pending. Treat `README.md`, `docs/requirements.md`, `docs/验收测试计划.md`, and `docs/工作进展记录.md` as the current source of truth.

## Planned Project Structure

Use the following structure unless a later architecture decision updates it:

```text
src/video_agent_skill/cli.py          CLI entry, I/O isolation, global exception mapping
src/video_agent_skill/core/extractor.py       yt-dlp Python API wrapper for probing, subtitles, audio
src/video_agent_skill/core/transcriber.py     VAD slicing, SenseVoice ASR, transcript cleanup
src/video_agent_skill/core/summarizer.py      OpenAI-compatible LLM client and JSON summary shaping
src/video_agent_skill/utils/config.py         config.yaml loading, proxy routing, runtime context
tests/                  Unit, integration, contract, and acceptance tests
docs/                   Product, requirements, architecture, plans, logs
config.example.yaml     Local template for proxy, LLM, and SenseVoice source path
```

Keep generated outputs, model caches, downloaded media, temp files, `dist/`, and local secrets out of source control unless explicitly used as small test fixtures.

## Commands And Tooling

Windows terminal commands in this workspace must follow `C:\Users\Administrator\.codex\RTK.md` and use the `rtk` prefix:

```powershell
rtk powershell -Command "uv run pytest tests/"
```

Expected implementation commands:

```powershell
uv run video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
uv run pytest tests/
uv build --wheel
pip install dist/video_agent_skill-*.whl
docker build -t video-agent-skill .
```

The scaffold commands are runnable. Real videos may still fail on external services, model loading, FFmpeg availability, or platform restrictions until end-to-end validation is complete.

## Coding Style

Use Python 3.10+ with strict type hints for public functions and methods. Prefer small modules, explicit imports, and dataclasses or typed dictionaries for internal contracts. Use `snake_case` for modules, functions, variables, and test files; use `PascalCase` for classes and exception types.

When scaffolding starts, add formatter and linter configuration. Prefer `ruff` for linting/formatting unless the project chooses another Python toolchain.

## Contract Requirements

The CLI is Agent-facing. Preserve these invariants:

- `stdout` must contain only one final JSON object.
- Logs, progress bars, warnings, third-party output, and debug text must go to `stderr`.
- Failures must return standard error JSON and a non-zero exit code.
- Raw audio/video must not be uploaded to third-party services.
- Temporary workspaces must be unique per run and cleaned by default.

## Testing Requirements

Prioritize contract and failure-path tests before broad refactors. At minimum, implementation must cover:

- CLI argument validation.
- `config.yaml` loading and proxy rule matching.
- Subtitle-first path and ASR fallback path.
- stdout JSON parseability with stderr noise present.
- mapped errors such as auth required, network timeout, CUDA OOM, and LLM timeout.
- default cleanup and `--keep-temp` behavior.

Follow `docs/验收测试计划.md` for MVP acceptance.

## Documentation And Progress Logging

Every design, implementation, testing, or documentation session must append a concise entry to `docs/工作进展记录.md`. Include date, operator, scope, files changed, verification status, remaining issues, and next action.

When changing behavior, update the relevant docs in the same session:

- Requirements changes: `docs/requirements.md`
- Acceptance changes: `docs/验收测试计划.md`
- User-facing commands: `README.md`, `README_CN.md`, `README_EN.md`
- Work history: `docs/工作进展记录.md`

## Security And Compliance

Never commit secrets, API keys, private cookies, paid-content URLs, full sensitive local paths, or downloaded restricted media. Do not implement bypasses for paid, private, or unauthorized content; return a clear authorization error instead.

### Git Hooks Configuration

This repository includes a pre-commit hook template in `.githooks/` to detect secrets before committing.

**Enable the hooks**:

```bash
# Enable git to use hooks from .githooks/ directory
git config core.hooksPath .githooks
```

**Make the hook executable**:

```bash
chmod +x .githooks/pre-commit
```

The hook will scan staged files for common API key patterns (e.g., `sk-...`, `api_key: "..."`) before each commit and abort if secrets are detected.

### Git History Security

**Never commit files containing secrets to git**. Once committed, secrets persist in history even after deletion. Mitigation requires `git filter-branch` or `git filter-repo` to rewrite history, which is disruptive.

**Sensitive file patterns to never commit**:

| Pattern | Reason |
|---------|--------|
| `config.yaml` with `api_key: "sk-..."` | Real API keys |
| `*.local.yaml`, `*.secret.yaml`, `.env*` | Configuration with credentials |
| `.claude/settings.local.json` | Agent permission configs may contain keys |
| `~/.video-agent-skill/config.yaml` | User runtime config |
| `site-packages/**/config.yaml` | Installed package configs |

**Pre-commit checks (recommended)**:

```bash
# Install gitleaks or git-secrets
brew install gitleaks  # macOS
# or
pip install detect-secrets

# Run before first commit in a new clone
gitleaks detect --source . --verbose
```

**If a secret is accidentally committed**:

1. Immediately rotate the compromised key
2. Use `git filter-repo` to remove the file from history:
   ```bash
   pip install git-filter-repo
   git filter-repo --path config.yaml --invert-paths --force
   git push --force
   ```
3. Notify all collaborators to re-clone
4. Enable GitHub Secret Scanning in repository settings

**GitHub Secret Scanning**: Enable in repository Settings → Security → Secret scanning. GitHub will alert when secrets are pushed to any branch.

### Release And Packaging Rules

Before building any wheel (`uv build --wheel`) or distribution artifact, the following checks are mandatory:

- **No secrets in the package**: The wheel must never contain real API keys, tokens, cookies, or credentials. Run a full-content scan (e.g., search for known key prefixes like `sk-`) on the built `.whl` before accepting it as a release artifact.
- **config.yaml must be an empty template**: `src/video_agent_skill/config.yaml` is packaged into the wheel so pip uninstall removes it cleanly (it is in RECORD). It MUST contain `api_key: ""` (empty) and no real credentials. Before every build, verify this file has no keys.
- **No key in source defaults**: `DEFAULT_LLM_API_KEY` in `src/video_agent_skill/utils/config.py` must remain an empty string. Built-in keys are for development only and must be removed before any release build.
- **No key in prompt files**: Prompt template files (`prompts/*.txt`, `src/video_agent_skill/prompts/*.txt`) must not contain credentials.
- **config.example.yaml stays as documentation**: The example file shows all available options with empty values and explanatory comments. It is also packaged but is not the file users edit.
- If a key is found in a built artifact, the release is blocked. Rotate the compromised key immediately and rebuild after cleaning the source of leakage.
