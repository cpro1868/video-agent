import pytest
from video_agent_skill.core.anticrawler import AntiCrawlerHandler
from typing import Protocol


def test_anticrawler_handler_is_protocol():
    """Verify AntiCrawlerHandler is a Protocol."""
    assert issubclass(AntiCrawlerHandler, Protocol)
    

def test_protocol_has_required_methods():
    """Verify Protocol defines name, supports, and apply."""
    assert hasattr(AntiCrawlerHandler, 'name')
    assert hasattr(AntiCrawlerHandler, 'supports')
    assert hasattr(AntiCrawlerHandler, 'apply')