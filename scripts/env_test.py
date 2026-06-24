#!/usr/bin/env python3
"""Video-Agent-Skill 环境预检脚本

测试视频前运行，确认环境达标。任何一个环节失败就停止，不尝试解决。

Usage:
    python scripts/env_test.py

Exit codes:
    0 - 环境达标，可以测试视频
    1 - 环境不达标，修复后再测试
"""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# 从项目根目录加载 config.yaml
_SCRIPT_DIR = Path(__file__).parent.resolve()
_PROJECT_ROOT = _SCRIPT_DIR.parent
sys.path.insert(0, str(_PROJECT_ROOT))

from video_agent_skill.utils.config import (  # noqa: E402
    AppConfig,
    load_config,
    resolve_llm_config,
    resolve_proxy,
)


def _load_config() -> AppConfig:
    """从项目根目录加载 config.yaml，不存在则返回默认配置。"""
    config_path = _PROJECT_ROOT / "config.yaml"
    if config_path.exists():
        return load_config(str(config_path))
    return load_config()


def _fail(step: str, reason: str) -> dict:
    """记录失败结果，不再继续。"""
    return {"step": step, "passed": False, "reason": reason}


def _ok(step: str, detail: str) -> dict:
    """记录通过结果。"""
    return {"step": step, "passed": True, "detail": detail}


def check_proxy() -> dict:
    """检查代理：实际发 HTTP 请求测试连通性。"""
    config = _load_config()
    test_url = "https://www.youtube.com/watch?v=KGUXXUCV6S4"
    proxy = resolve_proxy(test_url, config)

    if not proxy or proxy == "direct":
        # 尝试环境变量兜底
        env_proxy = os.getenv("VIDEO_AGENT_PROXY")
        if env_proxy:
            proxy = env_proxy
        else:
            return _fail(
                "proxy",
                "未配置代理。YouTube 需要代理，"
                "请在 config.yaml 或环境变量 VIDEO_AGENT_PROXY 中配置",
            )

    # 实际测试代理连通性
    try:
        proxy_handler = urllib.request.ProxyHandler({"http": proxy, "https": proxy})
        opener = urllib.request.build_opener(proxy_handler)
        req = urllib.request.Request("https://www.google.com", method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0")
        with opener.open(req, timeout=10) as resp:
            if resp.status in (200, 301, 302):
                return _ok("proxy", f"代理连通正常 ({proxy})")
            return _fail("proxy", f"代理返回异常 HTTP {resp.status}")
    except Exception as exc:
        return _fail("proxy", f"代理连接失败: {exc}")


def check_llm() -> dict:
    """检查 LLM：实际发请求验证 API Key 是否有效。"""
    config = _load_config()
    llm = resolve_llm_config(config)

    if not llm.api_key:
        return _fail(
            "llm",
            "未配置 LLM API Key。"
            "请在 config.yaml 或环境变量 VIDEO_AGENT_LLM_API_KEY 中配置",
        )

    # 实际测试 LLM 连通性
    try:
        endpoint = llm.api_base.rstrip("/") + "/chat/completions"
        payload = {
            "model": llm.model_name,
            "messages": [{"role": "user", "content": "Hi"}],
            "max_tokens": 5,
        }
        body = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {llm.api_key}",
        }
        req = urllib.request.Request(endpoint, data=body, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if resp.status == 200:
                return _ok("llm", f"LLM 服务正常 ({llm.model_name})")
            return _fail("llm", f"LLM 返回异常 HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        if exc.code == 401:
            return _fail("llm", "LLM API Key 无效 (HTTP 401)")
        return _fail("llm", f"LLM 服务错误 HTTP {exc.code}")
    except Exception as exc:
        return _fail("llm", f"LLM 连接失败: {exc}")


def check_sensevoice() -> dict:
    """检查 SenseVoice 路径：本地模式才需要检查。"""
    config = _load_config()
    source_dir = config.ai.asr.source_dir

    if not source_dir:
        return _ok("sensevoice", "未配置本地路径，使用 FunASR 默认远程")

    path = Path(source_dir)
    if not path.exists():
        return _fail("sensevoice", f"SenseVoice 路径不存在: {source_dir}")

    if not (path / "model.py").exists():
        return _fail("sensevoice", f"SenseVoice 路径缺少 model.py: {source_dir}")

    return _ok("sensevoice", f"本地路径有效: {source_dir}")


def main() -> int:
    print("=" * 60)
    print("Video-Agent-Skill 环境预检")
    print(f"时间: {datetime.now().isoformat()}")
    print("=" * 60)

    # 按依赖顺序检查，前面失败后面跳过
    results = []

    # Step 1: 代理
    result = check_proxy()
    results.append(result)
    status = "[PASS]" if result["passed"] else "[FAIL]"
    print(f"\n{status} 代理连通性")
    if result["passed"]:
        print(f"      {result['detail']}")
    else:
        print(f"      失败原因: {result['reason']}")
        print("\n" + "=" * 60)
        print("[STOP] 环境不达标，请修复代理配置后再测试视频")
        print("=" * 60)
        return 1

    # Step 2: LLM
    result = check_llm()
    results.append(result)
    status = "[PASS]" if result["passed"] else "[FAIL]"
    print(f"\n{status} LLM 服务")
    if result["passed"]:
        print(f"      {result['detail']}")
    else:
        print(f"      失败原因: {result['reason']}")
        print("\n" + "=" * 60)
        print("[STOP] 环境不达标，请修复 LLM 配置后再测试视频")
        print("=" * 60)
        return 1

    # Step 3: SenseVoice
    result = check_sensevoice()
    results.append(result)
    status = "[PASS]" if result["passed"] else "[FAIL]"
    print(f"\n{status} SenseVoice 路径")
    if result["passed"]:
        print(f"      {result['detail']}")
    else:
        print(f"      失败原因: {result['reason']}")
        # SenseVoice 失败不阻止测试，因为可以用远程模式
        print("\n      [NOTE] SenseVoice 检查失败，但可以使用 FunASR 远程模式")

    # 全部通过
    print("\n" + "=" * 60)
    print("[OK] 环境达标，可以开始测试视频")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
