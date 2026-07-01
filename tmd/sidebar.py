from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.message import Message
from textual.widgets import DirectoryTree, Label, ListView, ListItem, Static
from textual.widget import Widget

from tmd.history import get_history


class Sidebar(Widget):
    """파일 탐색기 + 최근 파일 목록 사이드바."""

    DEFAULT_CSS = """
    Sidebar {
        width: 30%;
        border-right: solid grey30;
    }
    Sidebar Label {
        padding: 0 1;
        background: grey15;
        color: bright_cyan;
        text-style: bold;
    }
    Sidebar ListView {
        height: auto;
        max-height: 10;
        border-bottom: solid grey30;
    }
    """

    @dataclass
    class FileSelected(Message):
        path: str

    def __init__(self, root: str | None = None, **kwargs):
        super().__init__(**kwargs)
        self._root = root or str(Path.cwd())

    def compose(self) -> ComposeResult:
        yield Label("최근 파일")
        yield ListView(id="recent-list")
        yield Label("파일 탐색기")
        yield DirectoryTree(self._root, id="dir-tree")

    def on_mount(self) -> None:
        self.refresh_history()

    def refresh_history(self) -> None:
        lv = self.query_one("#recent-list", ListView)
        lv.clear()
        for entry in get_history():
            p = entry["path"]
            lv.append(ListItem(Static(Path(p).name), id=f"hist-{p}"))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        item_id = event.item.id or ""
        if item_id.startswith("hist-"):
            path = item_id[len("hist-"):]
            self.post_message(self.FileSelected(path=path))

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self.post_message(self.FileSelected(path=str(event.path)))
