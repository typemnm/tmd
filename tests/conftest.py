import pytest


@pytest.fixture(autouse=True)
def isolate_history(tmp_path, monkeypatch):
    """Never let tests read or mutate the user's real recent-file history."""
    monkeypatch.setattr("tmd_cli.history.HISTORY_FILE", tmp_path / ".tmd_history")
