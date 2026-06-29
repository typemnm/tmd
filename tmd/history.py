import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_FILE = Path.home() / ".tmd_history"
MAX_ENTRIES = 20


def _load() -> list[dict]:
    if not HISTORY_FILE.exists():
        return []
    try:
        return json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def _save(entries: list[dict]) -> None:
    HISTORY_FILE.write_text(json.dumps(entries, indent=2), encoding="utf-8")


def add_to_history(path: str) -> None:
    entries = [e for e in _load() if e["path"] != path]
    entries.insert(0, {
        "path": path,
        "last_opened": datetime.now(timezone.utc).isoformat(),
    })
    _save(entries[:MAX_ENTRIES])


def get_history() -> list[dict]:
    entries = _load()
    valid = [e for e in entries if Path(e["path"]).exists()]
    if len(valid) != len(entries):
        _save(valid)
    return valid
