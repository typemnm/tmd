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
        border-right: solid #4e4e4e;
    }
    Sidebar Label {
        padding: 0 1;
        background: #262626;
        color: ansi_bright_cyan;
        text-style: bold;
    }
    Sidebar ListView {
        height: auto;
        max-height: 10;
        border-bottom: solid #4e4e4e;
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

    async def on_mount(self) -> None:
        self._history_paths: list[str] = []
        await self.refresh_history()

    async def refresh_history(self) -> None:
        lv = self.query_one("#recent-list", ListView)
        await lv.clear()
        self._history_paths = []
        for entry in get_history():
            p = entry["path"]
            self._history_paths.append(p)
            lv.append(ListItem(Static(Path(p).name)))

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "recent-list":
            return
        idx = event.index
        if 0 <= idx < len(self._history_paths):
            self.post_message(self.FileSelected(path=self._history_paths[idx]))

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        self.post_message(self.FileSelected(path=str(event.path)))
