import pytest
from video_agent_skill.core.plugin_registry import PluginRegistry


def test_singleton_pattern():
    """Verify PluginRegistry returns same instance."""
    registry1 = PluginRegistry.instance()
    registry2 = PluginRegistry.instance()
    assert registry1 is registry2


def test_get_danmaku_provider_returns_none_for_unsupported_url():
    """When no provider supports URL, return None."""
    registry = PluginRegistry()
    registry._danmaku_providers = []
    result = registry.get_danmaku_provider("https://unknown.site/video")
    assert result is None


def test_list_danmaku_providers_returns_empty_when_no_plugins():
    """When no plugins loaded, return empty list."""
    registry = PluginRegistry()
    registry._danmaku_providers = []
    result = registry.list_danmaku_providers()
    assert result == []


def test_list_anticrawler_handlers_returns_empty_when_no_plugins():
    """When no anticrawler handlers loaded, return empty list."""
    registry = PluginRegistry()
    registry._anticrawler_handlers = []
    result = registry.list_anticrawler_handlers()
    assert result == []


def test_get_anticrawler_handlers_returns_empty_when_no_plugins():
    """When no handlers loaded, return empty list."""
    registry = PluginRegistry()
    registry._anticrawler_handlers = []
    result = registry.get_anticrawler_handlers("https://bilibili.com/video/BV123")
    assert result == []