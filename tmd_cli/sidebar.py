from __future__ import annotations

import asyncio
from dataclasses import dataclass
from pathlib import Path

from textual.app import ComposeResult
from textual.message import Message
from textual.widget import Widget
from textual.widgets import Label, ListItem, ListView, Static, Tree
from textual.widgets.tree import TreeNode

from tmd_cli.history import get_history


class FileTree(Tree[Path]):
    """A small lazy file tree without a permanently running loader worker."""

    @dataclass
    class FileSelected(Message):
        path: Path

    def __init__(self, root: str, **kwargs) -> None:
        path = Path(root).expanduser().resolve()
        super().__init__(str(path), data=path, **kwargs)
        self._loaded_paths: set[Path] = set()

    def on_mount(self) -> None:
        self._populate_sync(self.root)
        self.root.expand()

    async def on_tree_node_expanded(self, event: Tree.NodeExpanded[Path]) -> None:
        event.stop()
        await self._populate(event.node)

    async def on_tree_node_selected(self, event: Tree.NodeSelected[Path]) -> None:
        event.stop()
        path = event.node.data
        if path is None:
            return
        if await asyncio.to_thread(path.is_file):
            self.post_message(self.FileSelected(path))
        elif await asyncio.to_thread(path.is_dir):
            await self._populate(event.node)
            event.node.toggle()

    async def _populate(self, node: TreeNode[Path]) -> None:
        path = node.data
        if path is None or path in self._loaded_paths:
            return
        self._loaded_paths.add(path)
        try:
            children = await asyncio.to_thread(
                lambda: sorted(
                    path.iterdir(),
                    key=lambda child: (not child.is_dir(), child.name.casefold()),
                )
            )
        except OSError:
            return
        for child in children:
            node.add(
                child.name,
                data=child,
                allow_expand=await asyncio.to_thread(child.is_dir),
            )

    def _populate_sync(self, node: TreeNode[Path]) -> None:
        """Populate the initial level during mount without startup workers."""
        path = node.data
        if path is None or path in self._loaded_paths:
            return
        self._loaded_paths.add(path)
        try:
            children = sorted(
                path.iterdir(),
                key=lambda child: (not child.is_dir(), child.name.casefold()),
            )
        except OSError:
            return
        for child in children:
            node.add(child.name, data=child, allow_expand=child.is_dir())


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
        yield FileTree(self._root, id="dir-tree")

    async def on_mount(self) -> None:
        self._history_paths: list[str] = []
        await self.refresh_history()

    async def refresh_history(self) -> None:
        lv = self.query_one("#recent-list", ListView)
        await lv.clear()
        entries = get_history()
        self._history_paths = [entry["path"] for entry in entries]
        items: list[ListItem] = []
        for path in self._history_paths:
            item = ListItem(Static(Path(path).name))
            item.tooltip = path
            items.append(item)
        if items:
            await lv.extend(items)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if event.list_view.id != "recent-list":
            return
        idx = event.index
        if 0 <= idx < len(self._history_paths):
            self.post_message(self.FileSelected(path=self._history_paths[idx]))

    def on_file_tree_file_selected(self, event: FileTree.FileSelected) -> None:
        self.post_message(self.FileSelected(path=str(event.path)))
