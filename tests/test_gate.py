import io

import pytest

from onrecord import cli
from onrecord.gate import branch_violations


def test_only_story_files_allowed():
    assert branch_violations(["incoming/1979-police-message/story.json",
                              "incoming/1985-queen-live-aid/story.json"]) == []


@pytest.mark.parametrize("path", [
    "onrecord/validate.py",
    "config.toml",
    ".github/workflows/gate.yml",
    "queue/x/manifest.json",
    "incoming/x/photos/a.jpg",
    "incoming/../onrecord/story.json",
    "incoming/x/sub/story.json",
    "state.json",
])
def test_anything_else_is_a_violation(path):
    assert branch_violations(["incoming/ok/story.json", path]) == [path]


def test_gate_check_command(monkeypatch, capsys):
    monkeypatch.setattr("sys.stdin", io.StringIO("incoming/a/story.json\nonrecord/validate.py\n"))
    assert cli.main(["gate-check"]) == 1
    assert "onrecord/validate.py" in capsys.readouterr().out
    monkeypatch.setattr("sys.stdin", io.StringIO("incoming/a/story.json\n"))
    assert cli.main(["gate-check"]) == 0
