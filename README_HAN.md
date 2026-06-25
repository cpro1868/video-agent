# Video-Agent-Skill 影片內容總結大師

<p align="center">
  <a href="README.md">简体中文</a> |<a href="README_HAN.md">繁體中文</a> | <a href="README_EN.md">English</a> | <a href="README_VI.md">Tiếng Việt</a>
</p>


<div align="center">
**給 AI Agent 裝上"看影片"的眼睛**

讓大模型 Agent 能直接"看懂"任何影片連結－優先秒級擷取字幕，無字幕時本地 ASR 轉寫，最後輸出結構化摘要。

</div>

---

## 這是什麼？

你有沒有遇到過這樣的場景：讓 AI 助手幫你總結一個 YouTube 或 B站影片，它只能無奈地回复"我無法訪問影片鏈接"？

**Video-Agent-Skill** 就是來解決這個問題的。它是一個命令行工具（CLI），專門給 AI Agent 當"影片閱讀器"——你丟給它一個影片鏈接，它幫你把影片內容變成結構化的文字摘要，AI Agent 就能像處理普通文本一樣處理影片了。

### 為什麼需要它？

| 痛點 | Video-Agent-Skill 的解法 |
|------|--------------------------|
| **雲端 API 按分鐘收費，還得上傳視訊** | 本機處理，零 API 成本（LLM 摘要除外），音訊不上傳任何第三方伺服器 |
| **瀏覽器插件無法被 Agent 自動調用** | 純命令列工具，Agent 直接調用，輸出標準 JSON |
| **下載整個影片太慢太佔空間** | 智慧降級：先抓字幕（秒級），沒字幕才下載低碼率音訊轉寫 |
| **GPU 顯存不夠跑長影片** | 自動 VAD 切片，30 秒一段，4GB 顯存也能跑 1 小時影片 |
| **多平台網路差異大** | 代理路由，依網域名稱配對策略，適配 YouTube、B站等平台 |

### 它怎麼工作的？

```
影片 URL ──→ 字幕優先提取（秒級）
 │
 ├─ 有字幕 ──→ 下載字幕文字 ──→ LLM 摘要 ──→ JSON/Markdown
 │
 └─ 無字幕 ──→ 下載低碼率音訊 ──→ VAD切片 ──→ 本地ASR轉寫 ──→ LLM 摘要
```

1. **字幕優先**：先嘗試抓取平台字幕（UP主精校字幕或自動字幕），有就走字幕通道，秒級響應。
2. **ASR 降級**：沒字幕才下載音頻，用阿里 SenseVoice 模型本地離線轉寫，不花錢、不洩隱私。
3. **LLM 摘要**：轉寫文字送給 OpenAI 相容的 LLM（如 MiniMax、Ollama），提煉出標題、摘要、關鍵要點、詳細內容、標籤。
4. **標準輸出**：結果以 JSON（給 Agent）或 Markdown（給人看）輸出，日誌全進 stderr 不干擾。

### 誰在用它？

- **Agent 開發者**：整合到 Dify、FastGPT、Claude Code 等編排框架，讓 Agent 處理視訊鏈接
- **極客/終端用戶**：本地終端直接調用，快速獲取長影片摘要
- **系統維護者**：設定代理路由、部署 Docker、調整 LLM 參數

---

## 核心能力

- **字幕優先**：優先取得 UP 主字幕或平台自動字幕，避免不必要的音訊下載和本地推理。
- **本地 ASR 降級**：無字幕時提取音頻，使用 `SenseVoiceSmall` 完成本地離線轉寫。
- **彈幕分析（B站）**：擷取並分析 B站彈幕，洞察大眾情感、熱門話題和觀眾畫像。
- **雙格式輸出**：支援 `json`（Agent 解析）和 `markdown`（人類閱讀）兩種輸出格式，透過 `--output-format` 或 `config.yaml` 設定。
- **Agent 等級 I/O 契約**：運行日誌、進度條和第三方函式庫輸出全部進入 `stderr`，`stdout` 只輸出一段純 JSON 或 Markdown。
- **代理路由**：依網域名稱配對代理策略，適配 YouTube、B站、抖音等平台的網路差異。
- **標準交付**：支援 `uv` 開發運行、`pip`/`pipx` 安裝和 Wheel 離線分發。

## 目錄結構

```text
src/video_agent_skill/cli.py CLI 入口、全域異常處理、stdout/stderr 隔離
src/video_agent_skill/core/extractor.py 視訊元資料嗅探、字幕擷取、音訊下載
src/video_agent_skill/core/transcriber.py VAD 切片、本地 ASR 推理、轉寫清洗
src/video_agent_skill/core/summarizer.py LLM 摘要產生、Markdown/JSON 雙格式解析
src/video_agent_skill/core/danmaku.py B站彈幕擷取與分析
src/video_agent_skill/utils/config.py config.yaml 載入、代理路由、CLI 參數覆蓋
src/video_agent_skill/utils/cache.py 結果緩存
src/video_agent_skill/utils/progress.py 進度回饋
src/video_agent_skill/utils/retry.py 錯誤重試
src/video_agent_skill/utils/logging.py 分級日誌
src/video_agent_skill/prompts/ 預設 prompt 模板（隨套件安裝）
tests/ 單元測試、整合測試和契約測試
docs/ 產品、需求、架構、詳細設計與規劃文檔
```

## 快速開始

```powershell
# 查看版本
video-agent --version

# 環境診斷（不需要 URL）
video-agent --doctor

# 基本用法（JSON 輸出到 stdout）
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh

# Markdown 輸出到文件
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --output-format markdown --output-file summary.md
```

## 命令列參數

| 參數 | 必填 | 說明 |
|------|------|------|
| `-u, --url` | 是 | 目標影片 URL |
| `-l, --lang` | 否 | 字幕嗅探和 LLM 輸出語言，預設 `zh`。支援 `zh`/`zh-Hant`/`en`/`ja`/`ko`/`vi`/`fr`/`de`/`es`/`pt`/`ru`/`th`/`ar`/`it`，詳見下方語言清單 |
| `--proxy` | 否 | 單次運行強制代理 |
| `--keep-temp` | 否 | 保留暫存檔案用於調試 |
| `--transcript-only` | 否 | 僅傳回轉寫文本，不呼叫 LLM |
| `--output-format` | 否 | `json`（預設）或 `markdown` |
| `--output-file` | 否 | 輸出檔案路徑，預設 stdout |
| `--llm-api-key` | 否 | LLM API Key |
| `--llm-api-base` | 否 | LLM API Base URL |
| `--llm-model` | 否 | LLM 模型名稱 |
| `--llm-system-prompt-file` | 否 | 系統 Prompt 檔案路徑 |
| `--llm-user-prompt-file` | 否 | 使用者 Prompt 檔案路徑 |
| `--asr-device` | 否 | ASR 設備：`auto`/`cuda`/`mps`/`cpu` |
| `--sensevoice-source-dir` | 否 | SenseVoice 原始碼目錄 |
| `--include-danmaku` | 否 | 啟用 B站彈幕分析 |
| `--danmaku-prompt-file` | 否 | 彈幕分析 Prompt 檔案路徑 |
| `--danmaku-output` | 否 | 彈幕分析獨立輸出檔 |
| `--batch` | 否 | 批次處理，從檔案讀取 URL 清單 |
| `--no-cache` | 否 | 停用本次執行的結果快取 |
| `--clear-cache` | 否 | 清理所有快取並退出 |
| `--no-progress-bar` | 否 | 停用視覺化進度條 |
| `--doctor` | 否 | 環境診斷，不需要 URL |
| `--version, -V` | 否 | 查看版本號 |
| `--prompt-info` | 否 | 查看包內預設 Prompt 資訊 |
| `--init-prompts [DIR]` | 否 | 複製預設 Prompt 到本機目錄 |
| `--init-config [DIR]` | 否 | 複製設定範本到指定目錄 |
| `--config` | 否 | 指定 config.yaml 路徑，預設讀包內 |

### 支援的語言

`--lang` 參數同時控製字幕嗅探語言和 LLM 摘要輸出語言：

| 語言代碼 | 輸出語言 | 說明 |
|----------|----------|------|
| `zh` | 簡體中文 | 預設值 |
| `zh-Hant` 或 `zh-TW` | 繁體中文 | |
| `en` | English | |
| `ja` | 日本文 | |
| `ko` | 한국어 | |
| `vi` | Tiếng Việt | |
| `fr` | Français | |
| `de` | Deutsch | |
| `es` | Español | |
| `pt` | Português | |
| `ru` | Русский | |
| `th` | ภาษาไทย | |
| `ar` | العربية | |
| `it` | Italiano | |

```powershell
# 輸出繁體中文摘要
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh-Hant

# 輸出日文摘要
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang ja

# 輸出越南語摘要
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang vi
```

> 未列出的語言代碼會作為 fallback 傳給 LLM，效果取決於 LLM 對該語言的支援程度。

Windows 環境下如遵循本倉庫 Agent 約定，請透過 `rtk` 執行指令：

```powershell
rtk powershell -Command "uv run video-agent -u 'https://www.youtube.com/watch?v=xxxx' --lang zh"
```

## 安裝與設定

### 環境需求

使用前請確認以下依賴已就緒：

| 依賴 | 用途 | 必需性 | 安裝方式 |
|------|------|--------|----------|
| **Python 3.10+** | 運作環境 | 必要 | 系統自帶或 conda 安裝 |
| **FFmpeg** | 音訊格式轉換（字幕頻道不需要，ASR 頻道必備） | ASR 頻道必要 | 加入系統 PATH |
| **yt-dlp** | 視訊元資料探測、字幕/音訊下載 | 必要（隨 pip 套件安裝） | `pip install yt-dlp` 或隨本套件安裝 |
| **PySocks** | SOCKS5 代理支援（存取 YouTube 需要） | 查看代理類型 | `pip install PySocks` 或隨本包安裝 |
| **FunASR + PyTorch** | 本地 ASR 轉寫引擎（SenseVoice 模型） | ASR 通道必要 | 請參閱下方"ASR 環境配置" |
| **LLM API Key** | LLM 摘要產生 | 摘要功能必需 | 請參閱下方"LLM 設定" |

> **說明**：如果影片有字幕，走字幕頻道不需要 ASR 環境，秒數回傳；只有無字幕影片才會降級到 ASR 頻道，此時才需要 FunASR + PyTorch。

### ASR 環境配置（無字幕影片需要）

ASR 轉寫使用阿里達摩院的 **SenseVoiceSmall** 模型，透過 **FunASR** 框架加載，依賴 **PyTorch**。這部分依賴較大（含 CUDA 支援），建議放在獨立的 conda 環境：

```powershell
# 1. 建立專用 conda 環境
conda create -n milvus python=3.10
conda activate milvus

# 2. 安裝 PyTorch（根據你的 GPU 選擇）
# 有 NVIDIA GPU（CUDA）：
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
# 無 GPU（CPU 模式，速度較慢）：
pip install torch torchaudio

# 3. 安裝 FunASR
pip install funasr

# 4. 安裝 FFmpeg 並加入 PATH
# Windows: 下載 https://ffmpeg.org/download.html，解壓縮後將 bin 目錄加入系統 PATH
# Linux: sudo apt install ffmpeg
# Mac: brew install ffmpeg

# 5. 安裝 video-agent-skill
pip install dist/video_agent_skill-*.whl

# 6. 驗證 ASR 環境
video-agent --doctor
# 輸出中 asr device 應顯示 cuda 或 cpu，funasr 顯示已安裝
```

**SenseVoice 原始碼目錄（可選）**：

預設 FunASR 會從 ModelScope 自動下載 `iic/SenseVoiceSmall` 模型。如果你有本機 SenseVoice 原始碼檢出（包含 `model.py`），可以在 config.yaml 中指定：

```yaml
ai:
 asr:
 source_dir: "G:/Projects/Sources/SenseVoice" # 包含 model.py 的目錄
```

或透過 CLI 參數指定：

```powershell
video-agent -u "..." --sensevoice-source-dir "G:/Projects/Sources/SenseVoice"
```

**ASR 設備選擇**：

```yaml
ai:
 asr:
 device: "auto" # 自動探測：cuda -> mps -> cpu
 # device: "cuda" # 強制使用 GPU
 # device: "cpu" # 強制使用 CPU
```

- `auto`：自動偵測，優先 `cuda`（NVIDIA GPU）→ `mps`（Apple Silicon）→ `cpu`
- `cuda`：強制 GPU，不可用則報錯
- `cpu`：強制 CPU，速度慢但相容性最好

### LLM 設定（摘要功能需要）

LLM 摘要使用 OpenAI 相容接口，預設配置為 MiniMax。你需要一個 API Key：

1. **取得 API Key**：到 [MiniMax 開放平台](https://www.minimaxi.com/) 註冊獲取
2. **填入設定**：編輯 `config.yaml` 的 `ai.llm.api_key` 字段

```yaml
ai:
 llm:
 api_base: "https://api.minimaxi.com/v1" # OpenAI 相容介面位址
 model_name: "MiniMax-M2.7" # 模型名稱
 api_key: "your-api-key-here" # 填入你的 API Key
 timeout_seconds: 60
```

也可以透過 CLI 參數傳入（覆蓋 config.yaml）：

```powershell
video-agent -u "..." --llm-api-key "your-api-key"
```

**換用其他 LLM**（如本地 Ollama）：

```yaml
ai:
 llm:
 api_base: "http://127.0.0.1:11434/v1" # Ollama 本機位址
 model_name: "qwen2.5" # 本地模型名
 api_key: "ollama" # Ollama 不需要真實 key，填任意值
```

### 安裝方式

#### 方式一：pip 安裝 Wheel 套件（建議）

```powershell
pip install dist/video_agent_skill-*.whl
video-agent --version
```

#### 方式二：pipx 全域安裝

```powershell
pipx install .
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

#### 方式三：uv 原始碼運行（開發調試）

```powershell
uv run video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

#### 方式四：Docker 容器化

```powershell
docker build -t video-agent-skill .
docker run --rm video-agent-skill -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

> **注意**：Dockerfile 已編寫，但尚未在真實環境中建置驗證。

### 首次使用檢查清單

安裝完成後，請依照以下步驟驗證：

```powershell
# 1. 查看版本
video-agent --version

# 2. 環境診斷（檢查 yt-dlp、FFmpeg、ASR、LLM 設定）
video-agent --doctor

# 3. 在目前目錄中產生設定檔和 prompt（方便編輯）
video-agent --setup

# 4. 編輯目前目錄的 config.yaml，填入 API Key、代理、ASR 路徑等

# 5. 測試字幕頻道（有字幕的 YouTube 影片，需要代理）
video-agent -u "https://www.youtube.com/watch?v=KGUXXUCV6S4" --lang en --proxy "http://127.0.0.1:7890" --transcript-only

# 6. 測試完整流程（LLM 摘要）
video-agent -u "https://www.youtube.com/watch?v=KGUXXUCV6S4" --lang zh --proxy "http://127.0.0.1:7890" --output-format markdown --output-file summary.md
```

### Wheel 發布規則

- `pyproject.toml` 必須定義專案名稱、版本號碼、依賴和 `video-agent` 控制台入口。
- 每次發布前必須執行契約測試，確保 `stdout` 仍為純 JSON。
- `config.yaml` 打入 wheel 但必須是空模板（`api_key: ""`），不得包含真實金鑰。
- `dist/` 中的建置產物不會直接提交到原始碼倉庫，除非用於正式 Release 附件。
- 版本號碼遵循語意化版本：`MAJOR.MINOR.PATCH`。

## 設定說明

### 設定載入規則

配置按以下優先權載入（高優先權覆蓋低優先權）：

| 優先權 | 來源 | 說明 |
|--------|------|------|
| 1 | CLI 參數 | `--proxy`、`--llm-api-key` 等覆蓋對應欄位 |
| 2 | 目前目錄 `./config.yaml` | 專案級覆蓋，以 `--setup` 產生 |
| 3 | 套件內 `config.yaml` | 預設設定（site-packages，pip uninstall 會清理） |

Prompt 範本同理：目前目錄 `./prompts/` 優先於包內 `prompts/`。

### 在目前目錄中產生配置

用 `--setup` 指令在目前工作目錄產生一套可編輯的設定和 prompt：

```powershell
# 產生 config.yaml 和 prompts/ 到目前目錄
video-agent --setup

# 覆蓋現有文件
video-agent --setup --overwrite
```

產生後直接編輯目前目錄的 `config.yaml` 即可，不影響套件內預設設定。

### 設定檔位置

- **目前目錄配置**：`./config.yaml`（以 `--setup` 生成，優先權高於套件內）
- **套件內預設配置**：`site-packages/video_agent_skill/config.yaml`（隨套件安裝）

查看包內配置路徑：

```powershell
python -c "import video_agent_skill; from pathlib import Path; print(Path(video_agent_skill.__file__).parent / 'config.yaml')"
```

### 設定範例

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
 device: "auto" # auto/cuda/mps/cpu
 model: "iic/SenseVoiceSmall" # FunASR 模型名
 source_dir: "G:/Projects/Sources/SenseVoice" # 本地 SenseVoice 原始碼目錄（可選）
 llm:
 api_base: "https://api.minimaxi.com/v1" # OpenAI 相容介面位址
 model_name: "MiniMax-M2.7" # 模型名稱
 api_key: "" # 填入你的 API Key
 timeout_seconds: 60
 system_prompt: "" # 留空用包內預設 prompt
 user_prompt_template: "" # 留空用包內預設 prompt

output:
 format: "markdown" # json 或 markdown
 file: ""
 batch_separator: "---"
```

### CLI 參數覆蓋

CLI 參數會覆寫 config.yaml 裡的對應欄位：

```powershell
# 用 --proxy 覆蓋 config 裡的代理設置
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --proxy "http://127.0.0.1:7890"

# 用 --llm-api-key 覆寫 config 裡的 api_key
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --llm-api-key "your-key"

# 用 --output-format 覆寫 config 裡的 format
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --output-format json

# 用 --asr-device 覆蓋 config 裡的 ASR 設備
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --asr-device cuda
```

## Prompt 模板

預設 prompt 檔案隨套件安裝在 `site-packages/video_agent_skill/prompts/`：

| 文件 | 用途 |
|------|------|
| `default-system.txt` | 系統 Prompt，定義 LLM 角色 |
| `default-video-summary.txt` | 影片摘要 Prompt，包含欄位規格和輸出範例 |
| `default-danmaku.txt` | 彈幕分析 Prompt（B站專屬） |

`default-video-summary.txt` 支援以下佔位符（由程式碼自動取代）：

| 佔位符 | 替換內容 |
|--------|----------|
| `{output_language}` | 輸出語言（如 `Simplified Chinese`） |
| `{language_instruction}` | 語言指令（如"必須使用簡體中文"） |
| `{transcript}` | 影片轉寫文字 |
| `{video_url}` | 影片 URL |
| `{video_duration}` | 影片長度（如 `1123秒`） |
| `{video_strategy}` | 處理策略（`subtitle` 或 `asr`） |
| `{video_language}` | 視訊語言 |

自訂 Prompt：

```powershell
# 查看包內預設 Prompt 訊息
video-agent --prompt-info

# 複製預設 Prompt 到本機目錄（可編輯）
video-agent --init-prompts ./my-prompts

# 使用自訂 Prompt 文件
video-agent -u "..." --lang zh \
 --llm-system-prompt-file "./my-prompts/default-system.txt" \
 --llm-user-prompt-file "./my-prompts/default-video-summary.txt"
```

## 輸出契約

### JSON 格式（預設）

成功時 `stdout` 只包含 JSON：

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
 "title": "具體的影片主題標題",
 "summary": "詳細的摘要段落...",
 "key_points": ["核心觀點1...", "核心觀點2..."],
 "detailed_content": [
 {"section_title": "小標題", "content": "詳細內容..."}
 ],
 "tags": ["AI", "Agent", "影片摘要"],
 "transcript_excerpt": "原文摘錄...",
 "markdown": "完整 Markdown 內容（output_format=markdown 時）"
 },
 "error": null
}
```

### Markdown 格式

使用 `--output-format markdown` 時，輸出人類可讀的結構化 Markdown 文檔，包含：標題、影片資訊、摘要、關鍵要點、詳細內容、標籤、轉錄片段。

失敗時同樣回傳 JSON，並使用非零退出碼：

```json
{
 "status": "error",
 "meta": {"url": "...", "strategy_used": "none", "language": "zh"},
 "content": null,
 "error": {"code": "AUTH_REQUIRED_ERROR", "message": "目標影片需要登入或付費權限"}
}
```

## 開發驗證

```powershell
uv run pytest tests/ # 單元測試
uv run ruff check . # 代碼檢查
uv build --wheel # 建構 wheel
video-agent --version # 查看版本
video-agent --doctor # 環境診斷
video-agent -u "<URL>" --lang zh --transcript-only # 僅轉寫
video-agent -u "<URL>" --lang zh --output-format markdown --output-file summary.md
```

關鍵驗收點：

- 帶字幕影片走 `subtitle` 通道並在 5 秒內返回。
- 無字幕影片走 `asr` 頻道，長音訊切片不觸發 GPU OOM。
- B站若僅暴露 `danmaku`，不視為可用 transcript 字幕，按無字幕影片降級到 ASR。
- 將 stdout 重新導向至檔案時，檔案內容可被 `json.loads` 直接解析。
- 斷網、鑑權失敗、LLM 逾時等異常均傳回標準錯誤 JSON。
- 預設執行結束後清理本次 UUID 暫存工作目錄。

## 文檔圖

| 文檔 | 說明 |
|------|------|
| `docs/工作進度記錄.md` | 每次設計、開發、測試和決策的持續記錄 |
| `docs/requirements.md` | 可驗收的軟體需求規格 |
| `docs/技術架構設計說明書.md` | 技術選用、邏輯架構與部署設計 |
| `docs/概要設計說明書.md` | 模組劃分、配置結構與資料協定 |
| `docs/詳細設計說明書.md` | 核心模組實作細節、錯誤碼與清理機制 |
| `docs/驗收測試計劃.md` | MVP 測試範圍、驗收用例、JSON 斷言和錯誤碼基線 |
| `docs/使用者使用說明書.md` | 詳細使用說明、參數詳解與 FAQ |
| `config.example.yaml` | 設定模板（含註解說明） |
| `AGENTS.md` | Agent 開髮指南與發布打包規則 |
