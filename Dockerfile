# syntax=docker/dockerfile:1

# 使用官方 Python 3.10 slim 镜像作为基础
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖：FFmpeg、git 等
# ffmpeg 用于音频格式转换（wav 等）
# git 用于 SenseVoice 模型下载
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    git \
    && rm -rf /var/lib/apt/lists/*

# 复制项目文件
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY prompts/ ./prompts/
COPY README.md ./

# 安装 uv（现代 Python 包管理器）
RUN pip install --no-cache-dir uv

# 使用 uv 安装项目依赖
RUN uv pip install --system -e .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 创建临时目录挂载点
VOLUME ["/tmp"]

# 设置入口点
ENTRYPOINT ["video-agent"]

# 默认参数（可选，运行时可覆盖）
CMD ["--help"]
