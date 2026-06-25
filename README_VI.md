# Video-Agent-Skill · Công cụ tóm tắt nội dung video

<p align="center">
  <a href="README.md">简体中文</a> |<a href="README_HAN.md">繁體中文</a> | <a href="README_EN.md">English</a> | <a href="README_VI.md">Tiếng Việt</a>
</p>


<div align="center">

**Trao cho AI Agent "đôi mắt xem video"**

Cho phép AI Agent "hiểu" bất kỳ liên kết video nào — trích xuất phụ đề trong vài giây, chuyển sang ASR cục bộ khi cần, và xuất tóm tắt có cấu trúc.

</div>

---

## Đây là gì?

Bạn đã bao giờ yêu cầu trợ lý AI tóm tắt một video YouTube hay Bilibili, chỉ để nhận lại câu trả lời "Tôi không thể truy cập liên kết video"?

**Video-Agent-Skill** giải quyết vấn đề đó. Đây là một công cụ dòng lệnh (CLI), đóng vai trò "trình đọc video" cho AI Agent — bạn đưa vào một liên kết video, nó biến nội dung video thành tóm tắt văn bản có cấu trúc, và AI Agent có thể xử lý video như văn bản thông thường.

### Tại sao cần nó?

| Nỗi đau | Giải pháp của Video-Agent-Skill |
|---------|--------------------------------|
| **API đám mây tính phí theo phút, phải tải video lên** | Xử lý cục bộ, chi phí API bằng không (trừ tóm tắt LLM), âm thanh không tải lên bên thứ ba |
| **Tiện ích trình duyệt không thể gọi tự động bởi Agent** | Công cụ CLI thuần, Agent gọi trực tiếp, xuất JSON tiêu chuẩn |
| **Tải cả video quá chậm, tốn dung lượng** | Phân cấp thông minh: lấy phụ đề trước (giây), chỉ tải âm thanh bitrate thấp khi không có phụ đề |
| **VRAM GPU không đủ cho video dài** | Tự động cắt VAD, 30 giây một đoạn, chạy video 1 giờ với 4GB VRAM |
| **Khác biệt mạng giữa các nền tảng** | Định tuyến proxy, khớp theo tên miền, tương thích YouTube, Bilibili, v.v. |

### Nó hoạt động thế nào?

```
URL video ──→ Trích xuất phụ đề trước (giây)
               │
               ├─ Có phụ đề ──→ Tải văn bản phụ đề ──→ Tóm tắt LLM ──→ JSON/Markdown
               │
               └─ Không phụ đề ──→ Tải âm thanh bitrate thấp ──→ Cắt VAD ──→ ASR cục bộ ──→ Tóm tắt LLM
```

1. **Ưu tiên phụ đề**: Thử lấy phụ đề nền tảng (phụ đề của người tải lên hoặc tự động). Nếu có, dùng đường phụ đề, phản hồi trong vài giây.
2. **Dự phòng ASR**: Không có phụ đề? Tải âm thanh và chuyển văn bản cục bộ bằng mô hình SenseVoice — miễn phí, không rò rỉ quyền riêng tư.
3. **Tóm tắt LLM**: Cung cấp bản chuyển văn bản cho LLM tương thích OpenAI (ví dụ: MiniMax, Ollama) để trích xuất tiêu đề, tóm tắt, điểm chính, nội dung chi tiết, thẻ.
4. **Xuất tiêu chuẩn**: Kết quả dạng JSON (cho Agent) hoặc Markdown (cho người đọc). Tất cả nhật ký vào stderr, không làm bẩn stdout.

### Ai sử dụng?

- **Lập trình viên Agent**: Tích hợp vào Dify, FastGPT, Claude Code và các khung điều phối khác
- **Người dùng nâng cao**: Chạy từ terminal để tóm tắt video nhanh
- **Người bảo trì hệ thống**: Cấu hình định tuyến proxy, triển khai Docker, tinh chỉnh tham số LLM

---

## Tính năng cốt lõi

- **Ưu tiên phụ đề**: Lấy phụ đề của người tải lên hoặc phụ đề tự động, tránh tải âm thanh và xử lý cục bộ không cần thiết.
- **Dự phòng ASR cục bộ**: Khi không có phụ đề, trích xuất âm thanh và chuyển văn bản cục bộ bằng `SenseVoiceSmall`.
- **Phân tích đạn mạc (Bilibili)**: Trích xuất và phân tích đạn mạc, hiểu cảm xúc khán giả, chủ đề nóng và hồ sơ người xem.
- **Xuất hai định dạng**: Hỗ trợ `json` (Agent phân tích) và `markdown` (người đọc) qua `--output-format` hoặc `config.yaml`.
- **Giao diện I/O cấp Agent**: Nhật ký, thanh tiến trình và đầu ra thư viện bên thứ ba vào `stderr`; `stdout` chỉ chứa một đối tượng JSON hoặc Markdown.
- **Định tuyến proxy**: Khớp quy tắc proxy theo tên miền cho YouTube, Bilibili, Douyin, v.v.
- **Giao phân phối tiêu chuẩn**: Hỗ trợ phát triển `uv`, cài đặt `pip`/`pipx` và phân phối ngoại tuyến Wheel.

## Cấu trúc thư mục

```text
src/video_agent_skill/cli.py            Điểm vào CLI, xử lý ngoại lệ toàn cục, cách ly stdout/stderr
src/video_agent_skill/core/extractor.py Thăm dò siêu dữ liệu, trích xuất phụ đề, tải âm thanh
src/video_agent_skill/core/transcriber.py Cắt VAD, suy luận ASR cục bộ, làm sạch bản chuyển
src/video_agent_skill/core/summarizer.py Tạo tóm tắt LLM, phân tích hai định dạng Markdown/JSON
src/video_agent_skill/core/danmaku.py   Trích xuất và phân tích đạn mạc Bilibili
src/video_agent_skill/utils/config.py   Tải config.yaml, định tuyến proxy, ghi đè tham số CLI
src/video_agent_skill/utils/cache.py    Bộ đệm kết quả
src/video_agent_skill/utils/progress.py Báo cáo tiến trình
src/video_agent_skill/utils/retry.py    Thử lại khi lỗi
src/video_agent_skill/utils/logging.py  Nhật ký phân cấp
src/video_agent_skill/prompts/          Mẫu prompt mặc định (cài đặt cùng gói)
tests/                                  Kiểm thử đơn vị, tích hợp và hợp đồng
docs/                                   Tài liệu sản phẩm, yêu cầu, kiến trúc, thiết kế và kế hoạch
```

## Bắt đầu nhanh

```powershell
# Xem phiên bản
video-agent --version

# Chẩn đoán môi trường (không cần URL)
video-agent --doctor

# Sử dụng cơ bản (xuất JSON ra stdout)
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh

# Xuất Markdown ra file
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh --output-format markdown --output-file summary.md
```

## Tham số dòng lệnh

| Tham số | Bắt buộc | Mô tả |
|---------|----------|-------|
| `-u, --url` | Có | URL video mục tiêu |
| `-l, --lang` | Không | Ngôn ngữ phụ đề và xuất tóm tắt LLM, mặc định `zh`. Hỗ trợ `zh`/`zh-Hant`/`en`/`ja`/`ko`/`vi`/`fr`/`de`/`es`/`pt`/`ru`/`th`/`ar`/`it`, xem danh sách bên dưới |
| `--proxy` | Không | Proxy bắt buộc cho lần chạy này |
| `--keep-temp` | Không | Giữ file tạm để gỡ lỗi |
| `--transcript-only` | Không | Chỉ trả về bản chuyển văn bản, bỏ qua LLM |
| `--output-format` | Không | `json` (mặc định) hoặc `markdown` |
| `--output-file` | Không | Đường dẫn file xuất, mặc định stdout |
| `--llm-api-key` | Không | LLM API Key |
| `--llm-api-base` | Không | LLM API Base URL |
| `--llm-model` | Không | Tên mô hình LLM |
| `--llm-system-prompt-file` | Không | Đường dẫn file prompt hệ thống |
| `--llm-user-prompt-file` | Không | Đường dẫn file prompt người dùng |
| `--asr-device` | Không | Thiết bị ASR: `auto`/`cuda`/`mps`/`cpu` |
| `--sensevoice-source-dir` | Không | Thư mục mã nguồn SenseVoice |
| `--include-danmaku` | Không | Bật phân tích đạn mạc Bilibili |
| `--danmaku-prompt-file` | Không | File prompt phân tích đạn mạc |
| `--danmaku-output` | Không | File xuất riêng phân tích đạn mạc |
| `--batch` | Không | Xử lý hàng loạt URL từ file |
| `--no-cache` | Không | Tắt bộ đệm kết quả cho lần này |
| `--clear-cache` | Không | Xóa tất cả bộ đệm và thoát |
| `--no-progress-bar` | Không | Tắt thanh tiến trình trực quan |
| `--doctor` | Không | Chẩn đoán môi trường, không cần URL |
| `--version, -V` | Không | Xem phiên bản |
| `--prompt-info` | Không | Xem thông tin prompt mặc định trong gói |
| `--init-prompts [DIR]` | Không | Sao chép prompt mặc định ra thư mục địa phương |
| `--init-config [DIR]` | Không | Sao chép mẫu cấu hình ra thư mục chỉ định |
| `--config` | Không | Chỉ định đường dẫn config.yaml, mặc định đọc trong gói |

### Ngôn ngữ được hỗ trợ

Tham số `--lang` đồng thời điều khiển ngôn ngữ phụ đề và ngôn ngữ xuất tóm tắt LLM:

| Mã | Ngôn ngữ xuất | Ghi chú |
|----|---------------|---------|
| `zh` | Tiếng Trung giản thể | Mặc định |
| `zh-Hant` hoặc `zh-TW` | Tiếng Trung phồn thể | |
| `en` | Tiếng Anh | |
| `ja` | Tiếng Nhật | |
| `ko` | Tiếng Hàn | |
| `vi` | Tiếng Việt | |
| `fr` | Tiếng Pháp | |
| `de` | Tiếng Đức | |
| `es` | Tiếng Tây Ban Nha | |
| `pt` | Tiếng Bồ Đào Nha | |
| `ru` | Tiếng Nga | |
| `th` | Tiếng Thái | |
| `ar` | Tiếng Ả Rập | |
| `it` | Tiếng Ý | |

```powershell
# Xuất tóm tắt tiếng Trung phồn thể
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh-Hant

# Xuất tóm tắt tiếng Nhật
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang ja

# Xuất tóm tắt tiếng Việt
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang vi
```

> Mã ngôn ngữ không có trong danh sách sẽ được truyền cho LLM sebagai fallback; kết quả phụ thuộc vào mức độ hỗ trợ của LLM cho ngôn ngữ đó.

## Cài đặt & Cấu hình

### Yêu cầu môi trường

Đảm bảo các phụ thuộc sau đã sẵn sàng trước khi sử dụng:

| Phụ thuộc | Mục đích | Bắt buộc | Cài đặt |
|-----------|---------|----------|---------|
| **Python 3.10+** | Môi trường chạy | Bắt buộc | Hệ thống hoặc conda |
| **FFmpeg** | Chuyển đổi định dạng âm thanh (đường phụ đề không cần, đường ASR cần) | Đường ASR | Thêm vào PATH hệ thống |
| **yt-dlp** | Thăm dò siêu dữ liệu video, tải phụ đề/âm thanh | Bắt buộc (cài cùng pip package) | `pip install yt-dlp` hoặc cùng gói này |
| **PySocks** | Hỗ trợ proxy SOCKS5 (cần cho YouTube) | Tùy loại proxy | `pip install PySocks` hoặc cùng gói này |
| **FunASR + PyTorch** | Engine ASR cục bộ (mô hình SenseVoice) | Đường ASR | Xem "Thiết lập môi trường ASR" bên dưới |
| **LLM API Key** | Tóm tắt LLM | Tính năng tóm tắt | Xem "Cấu hình LLM" bên dưới |

> **Lưu ý**: Nếu video có phụ đề, đường phụ đề không cần ASR — trả về trong vài giây. Chỉ video không phụ đề mới dự phòng xuống đường ASR, lúc đó mới cần FunASR + PyTorch.

### Thiết lập môi trường ASR (cho video không phụ đề)

Chuyển văn bản ASR dùng mô hình **SenseVoiceSmall** của Alibaba qua framework **FunASR**, phụ thuộc **PyTorch**. Các phụ thuộc này khá lớn (kèm CUDA), khuyến nghị dùng môi trường conda riêng:

```powershell
# 1. Tạo môi trường conda riêng
conda create -n milvus python=3.10
conda activate milvus

# 2. Cài PyTorch (chọn theo GPU)
# Có NVIDIA GPU (CUDA):
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu118
# Không có GPU (chế độ CPU, chậm hơn):
pip install torch torchaudio

# 3. Cài FunASR
pip install funasr

# 4. Cài FFmpeg và thêm vào PATH
# Windows: Tải từ https://ffmpeg.org/download.html, thêm bin vào PATH
# Linux:   sudo apt install ffmpeg
# Mac:     brew install ffmpeg

# 5. Cài video-agent-skill
pip install dist/video_agent_skill-*.whl

# 6. Kiểm tra môi trường ASR
video-agent --doctor
# Đầu ra asr device phải hiện cuda hoặc cpu, funasr hiện đã cài
```

**Thư mục mã nguồn SenseVoice (tùy chọn)**:

Mặc định FunASR tự tải mô hình `iic/SenseVoiceSmall` từ ModelScope. Nếu bạn có mã nguồn SenseVoice cục bộ (chứa `model.py`), chỉ định trong config.yaml:

```yaml
ai:
  asr:
    source_dir: "G:/Projects/Sources/SenseVoice"  # Thư mục chứa model.py
```

Hoặc qua tham số CLI:

```powershell
video-agent -u "..." --sensevoice-source-dir "G:/Projects/Sources/SenseVoice"
```

**Chọn thiết bị ASR**:

```yaml
ai:
  asr:
    device: "auto"  # Tự phát hiện: cuda -> mps -> cpu
    # device: "cuda"  # Bắt buộc GPU
    # device: "cpu"   # Bắt buộc CPU
```

- `auto`: Tự phát hiện, ưu tiên `cuda` (NVIDIA GPU) -> `mps` (Apple Silicon) -> `cpu`
- `cuda`: Bắt buộc GPU, báo lỗi nếu không có
- `cpu`: Bắt buộc CPU, chậm nhưng tương thích tốt nhất

### Cấu hình LLM (cho tính năng tóm tắt)

Tóm tắt LLM dùng giao diện tương thích OpenAI, mặc định MiniMax. Bạn cần API key:

1. **Lấy API key**: Đăng ký tại [Nền tảng mở MiniMax](https://www.minimaxi.com/)
2. **Điền vào cấu hình**: Sửa `ai.llm.api_key` trong config.yaml

```yaml
ai:
  llm:
    api_base: "https://api.minimaxi.com/v1"  # Endpoint tương thích OpenAI
    model_name: "MiniMax-M2.7"               # Tên mô hình
    api_key: "your-api-key-here"             # API key của bạn
    timeout_seconds: 60
```

Hoặc truyền qua tham số CLI (ghi đè config.yaml):

```powershell
video-agent -u "..." --llm-api-key "your-api-key"
```

**Dùng LLM khác** (ví dụ: Ollama cục bộ):

```yaml
ai:
  llm:
    api_base: "http://127.0.0.1:11434/v1"  # Địa chỉ Ollama cục bộ
    model_name: "qwen2.5"                   # Tên mô hình cục bộ
    api_key: "ollama"                       # Ollama không cần key thật, điền giá trị bất kỳ
```

### Phương thức cài đặt

#### Cách 1: pip cài Wheel (Khuyến nghị)

```powershell
pip install dist/video_agent_skill-*.whl
video-agent --version
```

#### Cách 2: Cài toàn cục bằng pipx

```powershell
pipx install .
video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

#### Cách 3: Chạy từ nguồn bằng uv (phát triển)

```powershell
uv run video-agent -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

#### Cách 4: Docker

```powershell
docker build -t video-agent-skill .
docker run --rm video-agent-skill -u "https://www.youtube.com/watch?v=xxxx" --lang zh
```

> **Lưu ý**: Dockerfile đã viết nhưng chưa build và kiểm tra trong môi trường thực.

### Danh sách kiểm tra lần đầu

Sau khi cài đặt, kiểm tra theo các bước sau:

```powershell
# 1. Xem phiên bản
video-agent --version

# 2. Chẩn đoán môi trường (kiểm tra yt-dlp, FFmpeg, ASR, cấu hình LLM)
video-agent --doctor

# 3. Tạo cấu hình và prompt trong thư mục hiện tại (dễ chỉnh sửa)
video-agent --setup

# 4. Sửa ./config.yaml — điền API Key, proxy, đường dẫn ASR, v.v.

# 5. Test đường phụ đề (video YouTube có phụ đề, cần proxy)
video-agent -u "https://www.youtube.com/watch?v=KGUXXUCV6S4" --lang en --proxy "http://127.0.0.1:7890" --transcript-only

# 6. Test toàn bộ luồng (tóm tắt LLM)
video-agent -u "https://www.youtube.com/watch?v=KGUXXUCV6S4" --lang zh --proxy "http://127.0.0.1:7890" --output-format markdown --output-file summary.md
```

## Cấu hình

### Quy tắc tải cấu hình

Cấu hình được tải theo ưu tiên (ưu tiên cao ghi đè ưu tiên thấp):

| Ưu tiên | Nguồn | Mô tả |
|---------|-------|-------|
| 1 | Tham số CLI | `--proxy`, `--llm-api-key`, v.v. ghi đè trường tương ứng |
| 2 | Thư mục hiện tại `./config.yaml` | Ghi đè cấp dự án, tạo bằng `--setup` |
| 3 | `config.yaml` trong gói | Mặc định (trong site-packages, pip uninstall sẽ xóa) |

Mẫu prompt cũng tương tự: `./prompts/` trong thư mục hiện tại ưu tiên hơn `prompts/` trong gói.

### Tạo cấu hình trong thư mục hiện tại

Dùng lệnh `--setup` để tạo cấu hình và prompt có thể chỉnh sửa trong thư mục làm việc hiện tại:

```powershell
# Tạo config.yaml và prompts/ trong thư mục hiện tại
video-agent --setup

# Ghi đè file đã có
video-agent --setup --overwrite
```

Sửa `config.yaml` đã tạo trực tiếp — không ảnh hưởng cấu hình mặc định trong gói.

### Ví dụ cấu hình

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
    model: "iic/SenseVoiceSmall"            # Tên mô hình FunASR
    source_dir: "G:/Projects/Sources/SenseVoice"  # Thư mục mã nguồn SenseVoice (tùy chọn)
  llm:
    api_base: "https://api.minimaxi.com/v1"  # Endpoint tương thích OpenAI
    model_name: "MiniMax-M2.7"              # Tên mô hình
    api_key: ""                             # Điền API Key của bạn
    timeout_seconds: 60
    system_prompt: ""                       # Để trống dùng mặc định trong gói
    user_prompt_template: ""                # Để trống dùng mặc định trong gói

output:
  format: "markdown"  # json hoặc markdown
  file: ""
  batch_separator: "---"
```

## Hợp đồng xuất

### Định dạng JSON (mặc định)

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
    "title": "Tiêu đề chủ đề video cụ thể",
    "summary": "Đoạn tóm tắt chi tiết...",
    "key_points": ["Điểm chính 1...", "Điểm chính 2..."],
    "detailed_content": [
      {"section_title": "Tiêu đề phần", "content": "Nội dung chi tiết..."}
    ],
    "tags": ["AI", "Agent", "tóm tắt video"],
    "transcript_excerpt": "Trích đoạn chuyển văn bản...",
    "markdown": "Toàn bộ nội dung Markdown (khi output_format=markdown)"
  },
  "error": null
}
```

### Định dạng Markdown

Dùng `--output-format markdown` để xuất Markdown có cấu trúc, dễ đọc cho người: tiêu đề, thông tin video, tóm tắt, điểm chính, nội dung chi tiết, thẻ, trích đoạn chuyển văn bản.

Khi lỗi cũng trả về JSON với mã thoát khác 0:

```json
{
  "status": "error",
  "meta": {"url": "...", "strategy_used": "none", "language": "zh"},
  "content": null,
  "error": {"code": "AUTH_REQUIRED_ERROR", "message": "Video yêu cầu đăng nhập hoặc truy cập trả phí"}
}
```

## Kiểm tra phát triển

```powershell
uv run pytest tests/                                    # Kiểm thử đơn vị
uv run ruff check .                                     # Kiểm tra code
uv build --wheel                                        # Build wheel
video-agent --version                                   # Xem phiên bản
video-agent --doctor                                    # Chẩn đoán môi trường
video-agent -u "<URL>" --lang zh --transcript-only      # Chỉ chuyển văn bản
video-agent -u "<URL>" --lang zh --output-format markdown --output-file summary.md
```

Điểm kiểm tra chấp nhận:

- Video có phụ đề dùng đường `subtitle` và trả về trong 5 giây.
- Video không phụ đề dùng đường `asr` không gây OOM GPU trên âm thanh dài.
- `danmaku` Bilibili không được coi là phụ đề transcript; những video đó dự phòng xuống ASR.
- stdout chuyển hướng có thể parse trực tiếp bằng `json.loads`.
- Lỗi mạng, xác thực, timeout LLM trả về JSON lỗi tiêu chuẩn.
- Thư mục làm việc UUID tạm thời được xóa mặc định sau mỗi lần chạy.

## Bản đồ tài liệu

| Tài liệu | Mô tả |
|----------|-------|
| `docs/工作进展记录.md` | Nhật ký liên tục cho thiết kế, phát triển, kiểm thử và quyết định |
| `docs/requirements.md` | Yêu cầu phần mềm có thể kiểm tra |
| `docs/技术架构设计说明书.md` | Lựa chọn công nghệ, kiến trúc logic và thiết kế triển khai |
| `docs/详细设计说明书.md` | Chi tiết triển khai cấp mô-đun, mã lỗi và thiết kế dọn dẹp |
| `docs/验收测试计划.md` | Phạm vi kiểm tra MVP, case chấp nhận, xác nhận JSON, baseline mã lỗi |
| `docs/用户使用说明书.md` | Hướng dẫn sử dụng chi tiết, tham chiếu tham số và FAQ |
| `config.example.yaml` | Mẫu cấu hình (kèm chú thích) |
| `AGENTS.md` | Hướng dẫn phát triển Agent và quy tắc đóng gói phát hành |
