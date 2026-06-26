from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from video_agent_skill.core.danmaku import DanmakuProvider
    from video_agent_skill.core.anticrawler import AntiCrawlerHandler

logger = logging.getLogger(__name__)


class PluginRegistry:
    """Plugin registry singleton for discovering and managing plugins.
    
    Loads plugins via importlib.metadata entry points on first access.
    """
    
    _instance: "PluginRegistry | None" = None
    
    def __init__(self) -> None:
        self._danmaku_providers: list[DanmakuProvider] = []
        self._anticrawler_handlers: list[AntiCrawlerHandler] = []
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
    
    def _load_anticrawler_plugins(self) -> None:
        """Discover and load anti-crawler handler plugins."""
        try:
            eps = entry_points(group="video_agent_skill.anticrawler")
            for ep in eps:
                try:
                    handler = ep.load()()
                    self._anticrawler_handlers.append(handler)
                    logger.info(f"Loaded anticrawler handler: {handler.name}")
                except Exception as exc:
                    logger.error(f"Failed to load anticrawler plugin {ep.name}: {exc}")
        except Exception as exc:
            logger.warning(f"entry_points scan failed: {exc}")
    
    def _ensure_loaded(self) -> None:
        """Lazily load all plugins on first access."""
        if not self._loaded:
            self._load_danmaku_plugins()
            self._load_anticrawler_plugins()
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
    
    def get_anticrawler_handlers(self, url: str) -> list[AntiCrawlerHandler]:
        """Get all anticrawler handlers that apply to URL."""
        self._ensure_loaded()
        return [h for h in self._anticrawler_handlers if h.supports(url)]
    
    def list_anticrawler_handlers(self) -> list[str]:
        """List all registered anticrawler handler names."""
        self._ensure_loaded()
        return [h.name for h in self._anticrawler_handlers]