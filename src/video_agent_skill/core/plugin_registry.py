from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_agent_skill.core.danmaku import DanmakuProvider

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Plugin registry singleton for discovering and managing plugins.
    
    Loads plugins via importlib.metadata entry points on first access.
    """
    
    _instance: "PluginRegistry | None" = None
    
    def __init__(self) -> None:
        self._danmaku_providers: list[DanmakuProvider] = []
        self._loaded = False
    
    @classmethod
    def instance(cls) -> "PluginRegistry":
        """Get or create the singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    def _load_danmaku_plugins(self) -> None:
        """Discover and load danmaku provider plugins."""
        try:
            eps = entry_points(group="video_agent_skill.danmaku")
            for ep in eps:
                try:
                    provider = ep.load()()
                    self._danmaku_providers.append(provider)
                    logger.info(f"Loaded danmaku provider: {provider.name}")
                except Exception as exc:
                    logger.error(f"Failed to load danmaku plugin {ep.name}: {exc}")
        except Exception as exc:
            logger.warning(f"entry_points scan failed: {exc}")
    
    def _ensure_loaded(self) -> None:
        """Lazily load all plugins on first access."""
        if not self._loaded:
            self._load_danmaku_plugins()
            self._loaded = True
    
    def get_danmaku_provider(self, url: str) -> DanmakuProvider | None:
        """Find danmaku provider that supports the given URL."""
        self._ensure_loaded()
        for provider in self._danmaku_providers:
            if provider.supports(url):
                return provider
        return None
    
    def list_danmaku_providers(self) -> list[str]:
        """List all registered danmaku provider names."""
        self._ensure_loaded()
        return [p.name for p in self._danmaku_providers]