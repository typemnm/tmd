from __future__ import annotations

from pathlib import Path

from rich.style import Style
from textual.binding import Binding
from textual.message import Message
from textual.timer import Timer
from textual.widgets import TextArea
from textual.widgets.text_area import TextAreaTheme

from tmd.history import add_to_history

_AUTOSAVE_DELAY = 2.0  # seconds


def _make_theme() -> TextAreaTheme:
    return TextAreaTheme(
        name="tmd-dark",
        base_style=Style(color="white", bgcolor="grey7"),
        gutter_style=Style(color="grey46", bgcolor="grey7"),
        cursor_style=Style(color="black", bgcolor="bright_cyan"),
        cursor_line_style=Style(bgcolor="grey15"),
        bracket_matching_style=Style(bgcolor="grey30"),
        selection_style=Style(bgcolor="grey30"),
    )


class MarkdownEditor(TextArea):
    """WYSIWYG-style markdown editor widget."""

    BINDINGS = [
        Binding("ctrl+s", "save", "저장"),
        Binding("ctrl+b", "toggle_bold", "굵게"),
        Binding("ctrl+i", "toggle_italic", "기울임"),
    ]

    class Saved(Message):
        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    class Modified(Message):
        pass

    def __init__(self, **kwargs) -> None:
        super().__init__("", show_line_numbers=True, **kwargs)
        self.current_path: str | None = None
        self._autosave_timer: Timer | None = None
        self._loading: bool = False

    def on_mount(self) -> None:
        self.register_theme(_make_theme())
        self.theme = "tmd-dark"

    def on_unmount(self) -> None:
        if self._autosave_timer is not None:
            self._autosave_timer.stop()
            self._autosave_timer = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_file(self, path: str) -> None:
        """Load *path* into the editor and record it in history."""
        self._loading = True
        try:
            content = Path(path).read_text(encoding="utf-8")
            self.load_text(content)
            self.current_path = path
            add_to_history(path)
        finally:
            self._loading = False

    def save_file(self) -> None:
        """Write the current buffer to *current_path*."""
        if self.current_path is None:
            return
        Path(self.current_path).write_text(self.text, encoding="utf-8")
        self.post_message(self.Saved(path=self.current_path))

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self._loading:
            return
        self.post_message(self.Modified())
        self._schedule_autosave()

    # ------------------------------------------------------------------
    # Actions (bound via BINDINGS)
    # ------------------------------------------------------------------

    def action_save(self) -> None:
        self.save_file()

    def action_toggle_bold(self) -> None:
        self._wrap_selection("**", "**")

    def action_toggle_italic(self) -> None:
        self._wrap_selection("*", "*")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _schedule_autosave(self) -> None:
        """Debounced autosave: reset the 2-second countdown on every change."""
        if self._autosave_timer is not None:
            self._autosave_timer.stop()
        if self.current_path is not None:
            self._autosave_timer = self.set_timer(_AUTOSAVE_DELAY, self.save_file)

    def _wrap_selection(self, prefix: str, suffix: str) -> None:
        """Toggle *prefix*/*suffix* markers around the current selection."""
        selected = self.selected_text
        if not selected:
            return
        sel = self.selection
        if selected.startswith(prefix) and selected.endswith(suffix):
            inner = selected[len(prefix) : len(selected) - len(suffix)]
            self.replace(inner, sel.start, sel.end)
        else:
            self.replace(f"{prefix}{selected}{suffix}", sel.start, sel.end)
