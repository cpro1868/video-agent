from __future__ import annotations

from video_agent_skill.cli import main


def test_list_plugins_command(capsys):
    result = main(["--list-plugins"])
    assert result == 0
    captured = capsys.readouterr()
    assert "Danmaku providers:" in captured.err


def test_list_plugins_command_stderr_only(capsys):
    main(["--list-plugins"])
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "Danmaku providers:" in captured.err