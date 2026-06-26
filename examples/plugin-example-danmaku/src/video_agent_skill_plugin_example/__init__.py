from video_agent_skill.core.danmaku import DanmakuItem, DanmakuProvider


class ExampleDanmakuProvider(DanmakuProvider):
    """Example plugin demonstrating plugin interface."""

    name = "example"

    def supports(self, url: str) -> bool:
        """This example doesn't support any real URLs."""
        return False

    def extract(self, url: str, *, proxy: str = "") -> list[DanmakuItem]:
        """Example extraction - replace with real implementation."""
        return []