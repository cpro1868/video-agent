# Video-Agent-Skill 视频内容总结大师

<div align="center">

**给 AI Agent 装上"看视频"的眼睛**

让大模型 Agent 能直接"看懂"任何视频链接——优先秒级提取字幕，无字幕时本地 ASR 转写，最后输出结构化摘要。

</div>

---

## 这是什么？

你有没有遇到过这样的场景：让 AI 助手帮你总结一个 YouTube 或 B站视频，它只能无奈地回复"我无法访问视频链接"？

**Video-Agent-Skill** 就是来解决这个问题的。它是一个命令行工具（CLI），专门给 AI Agent 当"视频阅读器"——你丢给它一个视频链接，它帮你把视频内容变成结构化的文字摘要，AI Agent 就能像处理普通文本一样处理视频了。

### 为什么需要它？

| 痛点 | Video-Agent-Skill 的解法 |
|------|--------------------------|
| **云端 API 按分钟收费，还得上传视频** | 本地处理，零 API 成本（LLM 摘要除外），音频不上传任何第三方服务器 |
| **浏览器插件无法被 Agent 自动调用** | 纯命令行工具，Agent 直接调用，输出标准 JSON |
| **下载整个视频太慢太占空间** | 智能降级：先抓字幕（秒级），没字幕才下载低码率音频转写 |
| **GPU 显存不够跑长视频** | 自动 VAD 切片，30 秒一段，4GB 显存也能跑 1 小时视频 |
| **多平台网络差异大** | 代理路由，按域名匹配策略，适配 YouTube、B站等平台 |

### 它怎么工作的？

```
视频 URL ──→ 字幕优先提取（秒级）
               │
               ├─ 有字幕 ──→ 下载字幕文本 ──→ LLM 摘要 ──→ JSON/Markdown
               │
               └─ 无字幕 ──→ 下载低码率音频 ──→ VAD切片 ──→ 本地ASR转写 ──→ LLM 摘要
```

1. **字幕优先**：先尝试抓取平台字幕（UP主精校字幕或自动字幕），有就走字幕通道，秒级响应。
2. **ASR 降级**：没字幕才下载音频，用阿里 SenseVoice 模型本地离线转写，不花钱、不泄隐私。
3. **LLM 摘要**：转写文本送给 OpenAI 兼容的 LLM（如 MiniMax、Ollama），提炼出标题、摘要、关键要点、详细内容、标签。
4. **标准输出**：结果以 JSON（给 Agent）或 Markdown（给人看）输出，日志全进 stderr 不干扰。

### 谁在用它？

- **Agent 开发者**：集成到 Dify、FastGPT、Claude Code 等编排框架，让 Agent 能处理视频链接
- **极客/终端用户**：本地终端直接调用，快速获取长视频摘要
- **系统维护者**：配置代理路由、部署 Docker、调整 LLM 参数

---

## 核心能力

- **字幕优先**：优先获取 UP 主字幕或平台自动字幕，避免不必要的音频下载和本地推理。
- **本地 ASR 降级**：无字幕时提取音频，使用 `SenseVoiceSmall` 完成本地离线转写。
- **弹幕分析（B站）**：提取并分析 B站弹幕，洞察大众情感、热点话题和观众画像。
- **双格式输出**：支持 `json`（Agent 解析）和 `markdown`（人类阅读）两种输出格式，通过 `--output-format` 或 `config.yaml` 配置。
- **Agent 级 I/O 契约**：运行日志、进度条和第三方库输出全部进入 `stderr`，`stdout` 仅输出一段纯 JSON 或 Markdown。
- **代理路由**：按域名匹配代理策略，适配 YouTube、B站、抖音等平台的网络差异。
- **标准交付**：支持 `uv` 开发运行、`pip`/`pipx` 安装和 Wheel 离线分发。

## 目录结构

```text
src/video_agent_skill/cli.py            CLI 入口、全局异常处理、stdout/stderr 隔离
src/video_agent_skill/core/extractor.py 视频元数据嗅探、字幕提取、音频下载
src/video_agent_skill/core/transcriber.py VAD 切片、本地 ASR 推理、转写清洗
src/video_agent_skill/core/summarizer.py LLM 摘要生成、Markdown/JSON 双格式解析
src/video_agent_skill/core/danmaku.py   B站弹幕提取与分析
src/video_agent_skill/utils/config.py   config.yaml 加载、代理路由、CLI 参数覆盖
src/video_agent_skill/utils/cache.py    结果缓存
src/video_agent_skill/utils/progress.py 进度反馈
src/video_agent_skill/utils/retry.py    错误重试
src/video_agent_skill/utils/logging.py  分级日志
src/video_agent_skill/prompts/          默认 prompt 模板（随包安装）
tests/                                  单元测试、集成测试和契约测试
docs/                                   产品、需求、架构、详细设计和计划文档
```

## 快速开始

```powershell
# 查看版本
video-agent --version

# 环境诊断（不需要 URL）
video-agent --doctor

# 基本用法（JSON 输出到 stdout）
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh

# Markdown 输出到文件
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --output-format markdown --output-file summary.md
```

## 命令行参数

| 参数 | 必填 | 说明 |
|------|------|------|
| `-u, --url` | 是 | 目标视频 URL |
| `-l, --lang` | 否 | 优先字幕语言，默认 `zh` |
| `--proxy` | 否 | 单次运行强制代理 |
| `--keep-temp` | 否 | 保留临时文件用于调试 |
| `--transcript-only` | 否 | 仅返回转写文本，不调用 LLM |
| `--output-format` | 否 | `json`（默认）或 `markdown` |
| `--output-file` | 否 | 输出文件路径，默认 stdout |
| `--llm-api-key` | 否 | LLM API Key |
| `--llm-api-base` | 否 | LLM API Base URL |
| `--llm-model` | 否 | LLM 模型名称 |
| `--llm-system-prompt-file` | 否 | 系统 Prompt 文件路径 |
| `--llm-user-prompt-file` | 否 | 用户 Prompt 文件路径 |
| `--asr-device` | 否 | ASR 设备：`auto`/`cuda`/`mps`/`cpu` |
| `--sensevoice-source-dir` | 否 | SenseVoice 源码目录 |
| `--include-danmaku` | 否 | 启用 B站弹幕分析 |
| `--danmaku-prompt-file` | 否 | 弹幕分析 Prompt 文件路径 |
| `--danmaku-output` | 否 | 弹幕分析独立输出文件 |
| `--batch` | 否 | 批量处理，从文件读取 URL 列表 |
| `--no-cache` | 否 | 禁用本次运行的结果缓存 |
| `--clear-cache` | 否 | 清理所有缓存并退出 |
| `--no-progress-bar` | 否 | 禁用可视化进度条 |
| `--doctor` | 否 | 环境诊断，不需要 URL |
| `--version, -V` | 否 | 查看版本号 |
| `--prompt-info` | 否 | 查看包内默认 Prompt 信息 |
| `--init-prompts [DIR]` | 否 | 复制默认 Prompt 到本地目录 |
| `--init-config [DIR]` | 否 | 复制配置模板到指定目录 |
| `--config` | 否 | 指定 config.yaml 路径，默认读包内 |

Windows 环境下如遵循本仓库 Agent 约定，请通过 `rtk` 执行命令：

```powershell
rtk powershell -Command "uv run video-agent -u 'https://www.youtube.com/watch?v=xxxx' --lang zh"
```

## 安装与发布方式

### 方式一：uv 源码运行

适合开发、调试和本地联调：

```powershell
uv run video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

### 方式二：pipx 全局安装

适合本机长期作为 CLI 工具使用：

```powershell
pipx install .
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

### 方式三：Wheel 包发布与安装

适合内网、离线环境或 Agent 平台统一分发：

```powershell
uv build --wheel
pip install dist/video_agent_skill-*.whl
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

Wheel 发布规则（详见 `AGENTS.md`）：

- `pyproject.toml` 必须定义项目名、版本号、依赖和 `video-agent` 控制台入口。
- 每次发布前必须运行契约测试，确保 `stdout` 仍为纯 JSON。
- `config.yaml` 打入 wheel 但必须是空模板（`api_key: ""`），不得含真实密钥。
- `dist/` 中的构建产物不直接提交到源码仓库，除非用于正式 Release 附件。
- 版本号遵循语义化版本：`MAJOR.MINOR.PATCH`。

### 方式四：Docker 容器化

适合企业 Agent 平台、CI 环境或统一运行时：

```powershell
docker build -t video-agent-skill .
docker run --rm video-agent-skill -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

> **注意**：Dockerfile 已编写，但尚未在真实环境中构建验证。

## 配置说明

### 配置加载规则

**配置只从包内 `config.yaml` 读取，CLI 参数覆盖对应字段。**

- 配置文件位置：`site-packages/video_agent_skill/config.yaml`（随包安装，pip uninstall 会清理）
- CLI 参数（如 `--proxy`、`--llm-api-key`）覆盖 config.yaml 里的对应字段
- 不读环境变量、不读当前目录

### 配置示例

安装后编辑 `site-packages/video_agent_skill/config.yaml`：

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
    api_key: ""  # 在这里填入你的 API Key
    timeout_seconds: 60
    system_prompt: ""
    user_prompt_template: ""

output:
  format: "markdown"  # json 或 markdown
  file: ""
  batch_separator: "---"
```

### CLI 参数覆盖

CLI 参数会覆盖 config.yaml 里的对应字段：

```powershell
# 用 --proxy 覆盖 config 里的代理设置
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --proxy "http://127.0.0.1:7890"

# 用 --llm-api-key 覆盖 config 里的 api_key
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --llm-api-key "your-key"

# 用 --output-format 覆盖 config 里的 format
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --output-format json
```

## Prompt 模板

默认 prompt 文件随包安装在 `site-packages/video_agent_skill/prompts/`：

| 文件 | 用途 |
|------|------|
| `default-system.txt` | 系统 Prompt，定义 LLM 角色 |
| `default-video-summary.txt` | 视频摘要 Prompt，包含字段规范和输出示例 |
| `default-danmaku.txt` | 弹幕分析 Prompt（B站专属） |

`default-video-summary.txt` 支持以下占位符（由代码自动替换）：

| 占位符 | 替换内容 |
|--------|----------|
| `{output_language}` | 输出语言（如 `Simplified Chinese`） |
| `{language_instruction}` | 语言指令（如"必须使用简体中文"） |
| `{transcript}` | 视频转写文本 |
| `{video_url}` | 视频 URL |
| `{video_duration}` | 视频时长（如 `1123秒`） |
| `{video_strategy}` | 处理策略（`subtitle` 或 `asr`） |
| `{video_language}` | 视频语言 |

自定义 Prompt：

```powershell
# 查看包内默认 Prompt 信息
video-agent --prompt-info

# 复制默认 Prompt 到本地目录（可编辑）
video-agent --init-prompts ./my-prompts

# 使用自定义 Prompt 文件
video-agent -u "..." --lang zh \
  --llm-system-prompt-file "./my-prompts/default-system.txt" \
  --llm-user-prompt-file "./my-prompts/default-video-summary.txt"
```

## 输出契约

### JSON 格式（默认）

成功时 `stdout` 只包含 JSON：

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
    "title": "具体的视频主题标题",
    "summary": "详细的摘要段落...",
    "key_points": ["核心观点1...", "核心观点2..."],
    "detailed_content": [
      {"section_title": "小标题", "content": "详细内容..."}
    ],
    "tags": ["AI", "Agent", "视频摘要"],
    "transcript_excerpt": "原文摘录...",
    "markdown": "完整 Markdown 内容（output_format=markdown 时）"
  },
  "error": null
}
```

### Markdown 格式

使用 `--output-format markdown` 时，输出人类可读的结构化 Markdown 文档，包含：标题、视频信息、摘要、关键要点、详细内容、标签、转录片段。

失败时同样返回 JSON，并使用非零退出码：

```json
{
  "status": "error",
  "meta": {"url": "...", "strategy_used": "none", "language": "zh"},
  "content": null,
  "error": {"code": "AUTH_REQUIRED_ERROR", "message": "目标视频需要登录或付费权限"}
}
```

## 开发验证

```powershell
uv run pytest tests/                                    # 单元测试
uv run ruff check .                                     # 代码检查
uv build --wheel                                        # 构建 wheel
video-agent --version                                   # 查看版本
video-agent --doctor                                    # 环境诊断
video-agent -u "<URL>" --lang zh --transcript-only      # 仅转写
video-agent -u "<URL>" --lang zh --output-format markdown --output-file summary.md
```

关键验收点：

- 带字幕视频走 `subtitle` 通道并在 5 秒内返回。
- 无字幕视频走 `asr` 通道，长音频切片不触发 GPU OOM。
- B站若仅暴露 `danmaku`，不视为可用 transcript 字幕，按无字幕视频降级到 ASR。
- 将 stdout 重定向到文件时，文件内容可被 `json.loads` 直接解析。
- 断网、鉴权失败、LLM 超时等异常均返回标准错误 JSON。
- 默认运行结束后清理本次 UUID 临时工作目录。

## 文档地图

| 文档 | 说明 |
|------|------|
| `docs/工作进展记录.md` | 每次设计、开发、测试和决策的持续记录 |
| `docs/requirements.md` | 可验收的软件需求规格 |
| `docs/技术架构设计说明书.md` | 技术选型、逻辑架构和部署设计 |
| `docs/概要设计说明书.md` | 模块划分、配置结构和数据协议 |
| `docs/详细设计说明书.md` | 核心模块实现细节、错误码和清理机制 |
| `docs/验收测试计划.md` | MVP 测试范围、验收用例、JSON 断言和错误码基线 |
| `docs/用户使用说明书.md` | 详细使用说明、参数详解和 FAQ |
| `config.example.yaml` | 配置模板（含注释说明） |
| `AGENTS.md` | Agent 开发指南和发布打包规则 |
