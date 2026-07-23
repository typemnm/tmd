import json
import os
import tempfile
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict

HISTORY_FILE = Path.home() / ".tmd_history"
MAX_ENTRIES = 20


class HistoryEntry(TypedDict):
    path: str
    last_opened: str


def _load() -> list[HistoryEntry]:
    if not HISTORY_FILE.exists():
        return []
    try:
        raw = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []

    if not isinstance(raw, list):
        return []

    entries: list[HistoryEntry] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        last_opened = entry.get("last_opened")
        if isinstance(path, str) and path and isinstance(last_opened, str):
            entries.append({"path": path, "last_opened": last_opened})
    return entries


def _save(entries: list[HistoryEntry]) -> None:
    """Atomically persist history so an interrupted write cannot corrupt it."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{HISTORY_FILE.name}.", dir=HISTORY_FILE.parent
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(entries, file, indent=2)
            file.write("\n")
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary_path, HISTORY_FILE)
    finally:
        temporary_path.unlink(missing_ok=True)


def add_to_history(path: str) -> None:
    normalized_path = str(Path(path).expanduser().resolve())
    entries = [e for e in _load() if e["path"] != normalized_path]
    entries.insert(0, {
        "path": normalized_path,
        "last_opened": datetime.now(UTC).isoformat(),
    })
    try:
        _save(entries[:MAX_ENTRIES])
    except OSError:
        # History is a convenience feature; it must never prevent opening a file.
        return


def get_history() -> list[HistoryEntry]:
    entries = _load()
    valid = [e for e in entries if Path(e["path"]).is_file()]
    if len(valid) != len(entries):
        with suppress(OSError):
            _save(valid)
    return valid
