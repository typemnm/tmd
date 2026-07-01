from __future__ import annotations

import argparse
from pathlib import Path

from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static
from textual.containers import Horizontal

from tmd.editor import MarkdownEditor
from tmd.sidebar import Sidebar


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #262626;
        color: #b2b2b2;
        padding: 0 1;
    }
    """

    def set_saved(self, path: str) -> None:
        self.update(f"● Saved  {path}")

    def set_modified(self) -> None:
        name = self.app.query_one(MarkdownEditor).current_path or ""
        self.update(f"○ Unsaved  {name}")

    def set_idle(self) -> None:
        self.update("tmd — Terminal Markdown Editor  |  F1: Help")


class TmdApp(App):
    CSS = """
    Horizontal { height: 1fr; }
    MarkdownEditor { width: 70%; }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("tab", "focus_next", "Next focus"),
        ("ctrl+backslash", "toggle_sidebar", "Toggle sidebar"),
        ("ctrl+n", "new_file", "New file"),
        ("ctrl+o", "open_file_dialog", "파일 열기"),
        ("f1", "show_help", "Help"),
    ]

    def __init__(
        self,
        initial_path: str | None = None,
        root: str | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self._initial_path = initial_path
        self._root = root

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        with Horizontal():
            yield Sidebar(root=self._root, id="sidebar")
            yield MarkdownEditor(id="editor")
        yield StatusBar(id="status")
        yield Footer()

    def on_mount(self) -> None:
        status = self.query_one(StatusBar)
        status.set_idle()
        if self._initial_path:
            self.query_one(MarkdownEditor).open_file(self._initial_path)
            status.set_saved(self._initial_path)

    async def on_sidebar_file_selected(self, event: Sidebar.FileSelected) -> None:
        editor = self.query_one(MarkdownEditor)
        editor.open_file(event.path)
        sidebar = self.query_one(Sidebar)
        await sidebar.refresh_history()
        self.query_one(StatusBar).set_saved(event.path)

    async def on_markdown_editor_saved(self, event: MarkdownEditor.Saved) -> None:
        self.query_one(StatusBar).set_saved(event.path)
        await self.query_one(Sidebar).refresh_history()

    def on_markdown_editor_modified(self, event: MarkdownEditor.Modified) -> None:
        self.query_one(StatusBar).set_modified()

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        sidebar.display = not sidebar.display

    def action_new_file(self) -> None:
        editor = self.query_one(MarkdownEditor)
        editor.load_text("")
        editor.current_path = None
        self.query_one(StatusBar).set_idle()

    def action_open_file_dialog(self) -> None:
        from textual.widgets import Input
        from textual.screen import ModalScreen

        class OpenDialog(ModalScreen):
            CSS = "OpenDialog { align: center middle; } Input { width: 60; }"

            def compose(self) -> ComposeResult:
                yield Input(placeholder="파일 경로 입력 후 Enter...")

            def on_input_submitted(self, event: Input.Submitted) -> None:
                self.dismiss(event.value)

        def open_path(path: str | None) -> None:
            if path:
                p = Path(path).expanduser()
                if p.is_file():
                    self.query_one(MarkdownEditor).open_file(str(p.resolve()))

        self.push_screen(OpenDialog(), open_path)

    def action_show_help(self) -> None:
        self.notify(
            "Ctrl+S: Save | Ctrl+Q: Quit | Ctrl+B: Bold | Ctrl+I: Italic"
            " | Ctrl+N: New | Ctrl+\\: Toggle Sidebar | F1: Help",
            title="tmd Keyboard Shortcuts",
            timeout=6,
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tmd",
        description="Terminal Markdown Editor — WYSIWYG markdown editor",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="File or directory path to open",
    )
    args = parser.parse_args()

    initial_path: str | None = None
    root: str | None = None

    if args.path:
        p = Path(args.path).expanduser().resolve()
        if p.is_dir():
            root = str(p)
        elif p.is_file():
            initial_path = str(p)
        else:
            parser.error(f"File or directory not found: {args.path}")

    TmdApp(initial_path=initial_path, root=root).run()


if __name__ == "__main__":
    main()
