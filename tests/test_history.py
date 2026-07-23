from pathlib import Path

import pytest

from tmd_cli.history import add_to_history, get_history


@pytest.fixture(autouse=True)
def tmp_history(tmp_path, monkeypatch):
    fake = tmp_path / ".tmd_history"
    monkeypatch.setattr("tmd_cli.history.HISTORY_FILE", fake)
    yield fake


def test_add_and_get(tmp_path):
    path = str(tmp_path / "note.md")
    Path(path).touch()
    add_to_history(path)
    entries = get_history()
    assert entries[0]["path"] == path
    assert "last_opened" in entries[0]


def test_deduplication(tmp_path):
    path = str(tmp_path / "note.md")
    Path(path).touch()
    add_to_history(path)
    add_to_history(path)
    assert len(get_history()) == 1


def test_most_recent_first(tmp_path):
    a = str(tmp_path / "a.md")
    Path(a).touch()
    b = str(tmp_path / "b.md")
    Path(b).touch()
    add_to_history(a)
    add_to_history(b)
    assert get_history()[0]["path"] == b


def test_max_20_entries(tmp_path):
    for i in range(25):
        p = str(tmp_path / f"f{i}.md")
        Path(p).touch()
        add_to_history(p)
    assert len(get_history()) <= 20


def test_missing_file_excluded(tmp_path):
    path = str(tmp_path / "ghost.md")
    add_to_history(path)  # 파일이 실제로 존재하지 않음
    assert get_history() == []
