"""Video-Agent-Skill package.

Configuration is loaded from (in priority order):
1. Current directory ./config.yaml (project-level override)
2. Bundled package config.yaml (default)

CLI parameters override corresponding fields. Prompt templates follow the
same pattern: ./prompts/ in the current directory takes priority over the
bundled package prompts/. Use `video-agent --setup` to generate config.yaml
and prompts/ in the current working directory.
"""

from __future__ import annotations

from video_agent_skill.core.danmaku import (
    DanmakuItem,
    DanmakuProvider,
    BilibiliDanmakuProvider,
)
from video_agent_skill.core.plugin_registry import PluginRegistry

__all__ = [
    "__version__",
    "DanmakuItem",
    "DanmakuProvider",
    "BilibiliDanmakuProvider",
    "PluginRegistry",
]

__version__ = "2.0.0rc0"
