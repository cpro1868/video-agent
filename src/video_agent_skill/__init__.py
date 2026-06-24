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

__all__ = ["__version__"]

__version__ = "1.1.0"
