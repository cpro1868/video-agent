import pytest
from video_agent_skill.core.anticrawler import AntiCrawlerHandler, BilibiliAntiCrawlerHandler
from typing import Protocol


def test_anticrawler_handler_is_protocol():
    """Verify AntiCrawlerHandler is a Protocol."""
    assert issubclass(AntiCrawlerHandler, Protocol)
    

def test_protocol_has_required_methods():
    """Verify Protocol defines name, supports, and apply."""
    assert hasattr(AntiCrawlerHandler, 'name')
    assert hasattr(AntiCrawlerHandler, 'supports')
    assert hasattr(AntiCrawlerHandler, 'apply')


def test_bilibili_handler_supports():
    handler = BilibiliAntiCrawlerHandler()
    assert handler.supports("https://bilibili.com/video/BV123")
    assert handler.supports("https://www.bilibili.com/video/BV456")
    assert handler.supports("http://bilibili.com/watch?v=abc")
    assert not handler.supports("https://youtube.com/watch?v=xxx")
    assert not handler.supports("https://example.com/bilibili")


def test_bilibili_handler_name():
    handler = BilibiliAntiCrawlerHandler()
    assert handler.name == "bilibili-412"


def test_bilibili_handler_returns_new_dict():
    handler = BilibiliAntiCrawlerHandler()
    original = {"key": "value"}
    result = handler.apply(original)
    assert result is not original
    assert "http_headers" in result


def test_bilibili_handler_adds_bilibili_headers():
    handler = BilibiliAntiCrawlerHandler()
    original = {}
    result = handler.apply(original)
    headers = result["http_headers"]
    assert headers.get("Origin") == "https://www.bilibili.com"
    assert headers.get("Referer") == "https://www.bilibili.com/"


def test_bilibili_handler_adds_cookie_file():
    handler = BilibiliAntiCrawlerHandler()
    original = {}
    result = handler.apply(original)
    assert "cookiefile" in result
    assert isinstance(result["cookiefile"], str)
    assert result["cookiefile"].endswith(".txt")


def test_bilibili_handler_preserves_existing_headers():
    handler = BilibiliAntiCrawlerHandler()
    original = {"http_headers": {"User-Agent": "test-agent"}}
    result = handler.apply(original)
    assert result["http_headers"]["User-Agent"] == "test-agent"
    assert result["http_headers"]["Origin"] == "https://www.bilibili.com"


def test_bilibili_handler_implements_protocol():
    """Verify BilibiliAntiCrawlerHandler implements AntiCrawlerHandler."""
    handler = BilibiliAntiCrawlerHandler()
    assert isinstance(handler, AntiCrawlerHandler)