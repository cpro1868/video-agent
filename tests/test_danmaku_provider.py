"""Tests for DanmakuProvider protocol and BilibiliDanmakuProvider."""

import pytest
from video_agent_skill.core.danmaku import (
    BilibiliDanmakuProvider,
    DanmakuItem,
    DanmakuProvider,
)


def test_bilibili_provider_supports():
    provider = BilibiliDanmakuProvider()
    assert provider.supports("https://bilibili.com/video/BV123")
    assert provider.supports("https://www.bilibili.com/video/BVxyz")
    assert not provider.supports("https://youtube.com/watch?v=xxx")
    assert not provider.supports("https://vimeo.com/123")


def test_bilibili_provider_name():
    provider = BilibiliDanmakuProvider()
    assert provider.name == "bilibili"


def test_bilibili_provider_is_provider():
    provider = BilibiliDanmakuProvider()
    assert isinstance(provider, DanmakuProvider)


def test_danmaku_item_is_hashable():
    item1 = DanmakuItem(
        text="hello",
        time=1.0,
        mode=1,
        color="16777215",
        size=25,
        timestamp=1234567890,
        pool=0,
        user_hash="abc123",
        dm_id=1,
    )
    item2 = DanmakuItem(
        text="hello",
        time=1.0,
        mode=1,
        color="16777215",
        size=25,
        timestamp=1234567890,
        pool=0,
        user_hash="abc123",
        dm_id=1,
    )
    assert item1 == item2
    assert hash(item1) == hash(item2)


def test_danmaku_item_frozen():
    item = DanmakuItem(
        text="test",
        time=1.0,
        mode=1,
        color="16777215",
        size=25,
        timestamp=0,
        pool=0,
        user_hash="",
        dm_id=0,
    )
    with pytest.raises(AttributeError):
        item.text = "changed"


def test_danmaku_item_defaults():
    item = DanmakuItem(
        text="hello",
        time=1.0,
        mode=1,
        color="16777215",
        size=25,
        timestamp=0,
        pool=0,
        user_hash="",
        dm_id=0,
    )
    assert item.likes == 0
    assert item.weight == 0