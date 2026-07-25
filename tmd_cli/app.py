from __future__ import annotations

import argparse
import asyncio
import webbrowser
from collections.abc import Callable
from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.suggester import Suggester
from textual.timer import Timer
from textual.widgets import Button, Footer, Header, Input, Label, Static

from tmd_cli import __version__
from tmd_cli.editor import EditorFileError, MarkdownEditor
from tmd_cli.preview import PreviewServer
from tmd_cli.sidebar import Sidebar

_PREVIEW_DEBOUNCE = 0.2  # seconds


class PathSuggester(Suggester):
    """Inline path completion for PathDialog's Input.

    Receives the raw (non-casefolded) value so the already-typed portion of
    the suggestion keeps the user's exact casing; matching itself is done
    case-insensitively against the real directory entries.
    """

    def __init__(self) -> None:
        super().__init__(case_sensitive=True, use_cache=False)

    async def get_suggestion(self, value: str) -> str | None:
        if not value:
            return None
        raw = Path(value).expanduser()
        if value.endswith("/"):
            parent = raw
            prefix = ""
        else:
            parent = raw.parent
            prefix = raw.name
        try:
            entries = await asyncio.to_thread(lambda: sorted(parent.iterdir()))
        except OSError:
            return None
        needle = prefix.casefold()
        for entry in entries:
            if entry.name.casefold().startswith(needle):
                suggestion_path = parent / entry.name
                is_dir = await asyncio.to_thread(suggestion_path.is_dir)
                suggestion = str(suggestion_path) + ("/" if is_dir else "")
                if value.startswith("~"):
                    home = str(Path.home())
                    if suggestion.startswith(home):
                        suggestion = "~" + suggestion[len(home):]
                return suggestion
        return None


class PathDialog(ModalScreen[str | None]):
    """Modal path input used for open and save-as operations."""

    DEFAULT_CSS = """
    PathDialog { align: center middle; }
    PathDialog > Vertical {
        width: 72;
        height: auto;
        padding: 1 2;
        border: round #00aaaa;
        background: #1c1c1c;
    }
    PathDialog Input { width: 1fr; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, title: str, placeholder: str, value: str = "") -> None:
        super().__init__()
        self._title = title
        self._placeholder = placeholder
        self._value = value

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self._title)
            yield Input(
                value=self._value,
                placeholder=self._placeholder,
                suggester=PathSuggester(),
                id="path",
            )

    def on_mount(self) -> None:
        self.query_one(Input).focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self.dismiss(event.value.strip() or None)

    def action_cancel(self) -> None:
        self.dismiss(None)


class UnsavedDialog(ModalScreen[str]):
    """Resolve changes in an untitled document before a destructive action."""

    DEFAULT_CSS = """
    UnsavedDialog { align: center middle; }
    UnsavedDialog > Vertical {
        width: 64;
        height: auto;
        padding: 1 2;
        border: round #d7af00;
        background: #1c1c1c;
    }
    UnsavedDialog Horizontal { height: auto; align-horizontal: right; }
    UnsavedDialog Button { margin-left: 1; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label("제목 없는 문서의 변경 사항을 저장하시겠습니까?")
            with Horizontal():
                yield Button("저장", id="save", variant="primary")
                yield Button("버리기", id="discard", variant="warning")
                yield Button("취소", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id or "cancel")

    def action_cancel(self) -> None:
        self.dismiss("cancel")


class OverwriteDialog(ModalScreen[bool]):
    DEFAULT_CSS = """
    OverwriteDialog { align: center middle; }
    OverwriteDialog > Vertical {
        width: 64;
        height: auto;
        padding: 1 2;
        border: round #d7af00;
        background: #1c1c1c;
    }
    OverwriteDialog Horizontal { height: auto; align-horizontal: right; }
    OverwriteDialog Button { margin-left: 1; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, path: str) -> None:
        super().__init__()
        self._path = path

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f"이미 존재하는 파일입니다. 덮어쓸까요?\n{self._path}")
            with Horizontal():
                yield Button("덮어쓰기", id="overwrite", variant="warning")
                yield Button("취소", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "overwrite")

    def action_cancel(self) -> None:
        self.dismiss(False)


class StatusBar(Static):
    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        background: #262626;
        color: #b2b2b2;
        padding: 0 1;
    }
    """

    _preview_url: str | None = None

    def _with_preview_suffix(self, text: str) -> str:
        if self._preview_url:
            return f"{text}  |  ● 미리보기 {self._preview_url}"
        return text

    def set_saved(self, path: str) -> None:
        self.update(self._with_preview_suffix(f"● Saved  {path}"))

    def set_modified(self) -> None:
        name = self.app.query_one(MarkdownEditor).current_path or "제목 없음"
        self.update(self._with_preview_suffix(f"○ Unsaved  {name}"))

    def set_new(self) -> None:
        self.update(self._with_preview_suffix("○ Unsaved  제목 없음"))

    def set_idle(self) -> None:
        self.update(self._with_preview_suffix("tmd — Terminal Markdown Editor  |  F1: Help"))

    def set_preview_url(self, url: str | None) -> None:
        self._preview_url = url
        editor = self.app.query_one(MarkdownEditor)
        if editor.current_path is None:
            self.set_new()
        elif editor.is_dirty:
            self.set_modified()
        else:
            self.set_saved(editor.current_path)


class TmdApp(App):
    # Textual's default command palette is bound to ctrl+p; tmd doesn't use
    # the command palette, so disable it to free ctrl+p for preview toggle.
    ENABLE_COMMAND_PALETTE = False

    CSS = """
    Horizontal { height: 1fr; }
    MarkdownEditor { width: 1fr; }
    """

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("tab", "focus_next", "Next focus"),
        ("ctrl+backslash", "toggle_sidebar", "Toggle sidebar"),
        ("ctrl+n", "new_file", "New file"),
        ("ctrl+o", "open_file_dialog", "파일 열기"),
        ("ctrl+f", "find", "검색"),
        ("ctrl+shift+s", "save_as", "다른 이름으로 저장"),
        ("ctrl+p", "toggle_preview", "미리보기"),
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
        self._preview: PreviewServer | None = None
        self._preview_timer: Timer | None = None

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
            self._open_path(self._initial_path)

    def on_sidebar_file_selected(self, event: Sidebar.FileSelected) -> None:
        self._resolve_changes(lambda: self._open_path(event.path))

    def on_markdown_editor_saved(self, event: MarkdownEditor.Saved) -> None:
        self.query_one(StatusBar).set_saved(event.path)
        self._refresh_history()

    def on_markdown_editor_modified(self, event: MarkdownEditor.Modified) -> None:
        self.query_one(StatusBar).set_modified()
        if self._preview is not None:
            self._schedule_preview_publish()

    def on_markdown_editor_save_requested(
        self, event: MarkdownEditor.SaveRequested
    ) -> None:
        self._prompt_save_as()

    def on_markdown_editor_save_failed(self, event: MarkdownEditor.SaveFailed) -> None:
        self._notify_file_error(event.error)

    def action_toggle_sidebar(self) -> None:
        sidebar = self.query_one(Sidebar)
        sidebar.display = not sidebar.display

    def action_toggle_preview(self) -> None:
        if self._preview is None:
            editor = self.query_one(MarkdownEditor)
            preview = PreviewServer(
                get_text=lambda: editor.text,
                title=editor.current_path or "제목 없음",
            )
            try:
                url = preview.start()
            except OSError as error:
                self.notify(
                    f"미리보기 서버를 열지 못했습니다: {error}", severity="error", timeout=8
                )
                return
            self._preview = preview
            webbrowser.open(url)
            self.query_one(StatusBar).set_preview_url(url)
            self.notify(f"미리보기 시작: {url}", timeout=6)
        else:
            self._preview.stop()
            self._preview = None
            self.query_one(StatusBar).set_preview_url(None)
            self.notify("미리보기 종료", timeout=3)

    def _schedule_preview_publish(self) -> None:
        if self._preview_timer is not None:
            self._preview_timer.stop()
        self._preview_timer = self.set_timer(_PREVIEW_DEBOUNCE, self._publish_preview)

    def _publish_preview(self) -> None:
        self._preview_timer = None
        if self._preview is not None:
            self._preview.publish(self.query_one(MarkdownEditor).text)

    def on_unmount(self) -> None:
        if self._preview is not None:
            self._preview.stop()
            self._preview = None

    def action_new_file(self) -> None:
        self._resolve_changes(self._new_document)

    def _new_document(self) -> None:
        editor = self.query_one(MarkdownEditor)
        editor.new_document()
        self.query_one(StatusBar).set_new()

    def action_open_file_dialog(self) -> None:
        def open_path(path: str | None) -> None:
            if path:
                p = Path(path).expanduser()
                if p.is_file():
                    self._resolve_changes(lambda: self._open_path(str(p.resolve())))
                else:
                    self.notify("파일을 찾을 수 없습니다.", severity="error")

        self.push_screen(
            PathDialog("파일 열기", "파일 경로 입력 후 Enter..."), open_path
        )

    def action_save_as(self) -> None:
        self._prompt_save_as()

    def action_find(self) -> None:
        self.push_screen(PathDialog("문서 검색", "검색어 입력 후 Enter..."), self._find_text)

    def action_quit(self) -> None:
        self._resolve_changes(self.exit)

    def action_show_help(self) -> None:
        self.notify(
            "Ctrl+S: Save | Ctrl+Q: Quit | Alt+B: Bold | Alt+I: Italic"
            " | Ctrl+Shift+S: Save As | Ctrl+N: New"
            " | Ctrl+F: Find | Ctrl+\\: Toggle Sidebar | Ctrl+P: 미리보기 | F1: Help",
            title="tmd Keyboard Shortcuts",
            timeout=6,
        )

    def _resolve_changes(self, continuation: Callable[[], None]) -> None:
        """Make the current document safe before switching or exiting."""
        editor = self.query_one(MarkdownEditor)
        if not editor.is_dirty:
            continuation()
            return

        if editor.current_path is not None:
            try:
                editor.save_file()
            except EditorFileError as error:
                self._notify_file_error(error)
                return
            continuation()
            return

        def resolved(choice: str | None) -> None:
            if choice == "discard":
                editor.discard_changes()
                continuation()
            elif choice == "save":
                self._prompt_save_as(continuation)

        self.push_screen(UnsavedDialog(), resolved)

    def _prompt_save_as(self, continuation: Callable[[], None] | None = None) -> None:
        editor = self.query_one(MarkdownEditor)
        initial = editor.current_path or ""

        def selected(path: str | None) -> None:
            if not path:
                return
            target = Path(path).expanduser().resolve()
            if not target.parent.is_dir():
                self.notify("상위 디렉터리가 존재하지 않습니다.", severity="error")
                return
            if target.is_dir():
                self.notify("디렉터리에는 저장할 수 없습니다.", severity="error")
                return

            def save() -> None:
                try:
                    editor.save_file(str(target))
                except EditorFileError as error:
                    self._notify_file_error(error)
                    return
                if continuation is not None:
                    continuation()

            if target.exists() and str(target) != editor.current_path:
                self.push_screen(OverwriteDialog(str(target)), lambda yes: save() if yes else None)
            else:
                save()

        self.push_screen(
            PathDialog("다른 이름으로 저장", "저장할 파일 경로...", initial),
            selected,
        )

    def _open_path(self, path: str) -> None:
        editor = self.query_one(MarkdownEditor)
        try:
            editor.open_file(path)
        except EditorFileError as error:
            self._notify_file_error(error)
            return
        self.query_one(StatusBar).set_saved(editor.current_path or path)
        self._refresh_history()

    def _find_text(self, needle: str | None) -> None:
        if not needle:
            return
        editor = self.query_one(MarkdownEditor)
        row, column = editor.cursor_location
        lines = editor.text.split("\n")
        start_offset = sum(len(line) + 1 for line in lines[:row]) + column
        index = editor.text.find(needle, start_offset)
        wrapped = False
        if index < 0:
            index = editor.text.find(needle)
            wrapped = index >= 0
        if index < 0:
            self.notify(f"찾을 수 없습니다: {needle}", severity="warning")
            return

        start = self._offset_to_location(editor.text, index)
        end = self._offset_to_location(editor.text, index + len(needle))
        editor.move_cursor(start)
        editor.move_cursor(end, select=True, center=True)
        editor.focus()
        if wrapped:
            self.notify("문서 처음부터 다시 검색했습니다.", timeout=2)

    @staticmethod
    def _offset_to_location(text: str, offset: int) -> tuple[int, int]:
        before = text[:offset]
        row = before.count("\n")
        column = len(before.rsplit("\n", 1)[-1])
        return row, column

    def _refresh_history(self) -> None:
        self.run_worker(
            self.query_one(Sidebar).refresh_history(),
            group="history-refresh",
            exclusive=True,
        )

    def _notify_file_error(self, error: EditorFileError) -> None:
        self.notify(str(error), title="파일 작업 실패", severity="error", timeout=8)


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="tmd",
        description="Terminal Markdown Editor — keyboard-first Markdown editor",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="File or directory path to open",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
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
            root = str(p.parent)
        else:
            parser.error(f"File or directory not found: {args.path}")

    TmdApp(initial_path=initial_path, root=root).run()


if __name__ == "__main__":
    main()
