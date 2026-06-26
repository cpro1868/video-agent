import pytest
from video_agent_skill.core.transcriber import AsrEngine
from typing import Protocol


def test_asr_engine_is_protocol():
    """Verify AsrEngine is a Protocol."""
    assert issubclass(AsrEngine, Protocol)


def test_protocol_has_required_methods():
    """Verify Protocol defines name and transcribe."""
    assert hasattr(AsrEngine, 'name')
    assert hasattr(AsrEngine, 'transcribe')