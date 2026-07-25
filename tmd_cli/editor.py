from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path

from rich.style import Style
from textual.binding import Binding
from textual.message import Message
from textual.timer import Timer
from textual.widgets import TextArea
from textual.widgets.text_area import TextAreaTheme

from tmd_cli.history import add_to_history
from tmd_cli.markdown import BLOCK_PATTERNS, INLINE_PATTERNS, annotate_document

_AUTOSAVE_DELAY = 2.0  # seconds

# Build a mapping from style string → Rich Style for all markdown tokens.
_MD_SYNTAX_STYLES: dict[str, Style] = {
    style_str: Style.parse(style_str)
    for _, style_str in BLOCK_PATTERNS + INLINE_PATTERNS
}


def _make_theme() -> TextAreaTheme:
    return TextAreaTheme(
        name="tmd-dark",
        base_style=Style(color="white", bgcolor="grey7"),
        gutter_style=Style(color="grey46", bgcolor="grey7"),
        cursor_style=Style(color="black", bgcolor="bright_cyan"),
        cursor_line_style=Style(bgcolor="grey15"),
        bracket_matching_style=Style(bgcolor="grey30"),
        selection_style=Style(bgcolor="grey30"),
        syntax_styles=dict(_MD_SYNTAX_STYLES),
    )


class EditorFileError(OSError):
    """A user-facing file operation error."""

    def __init__(self, operation: str, path: str, cause: BaseException) -> None:
        self.operation = operation
        self.path = path
        self.cause = cause
        super().__init__(f"{operation} failed for {path}: {cause}")


class UnsavedChangesError(RuntimeError):
    """Raised when replacing a dirty document without resolving its changes."""


class MarkdownEditor(TextArea):
    """Markdown editor widget with syntax styling and safe persistence."""

    # On terminals without the Kitty keyboard protocol (most terminals,
    # including anything using legacy/xterm-style input), a physical Ctrl+I
    # keystroke is reported as the same raw byte as Tab, and Textual's ANSI
    # parser names that byte "tab" — BINDINGS matching is a literal string
    # match on event.key with no alias expansion (KEY_ALIASES only affects
    # key_*-method dispatch), so a Binding("ctrl+i", ...) was unreliable
    # across terminals (it only fires on terminals that opt into Kitty-style
    # key disambiguation, e.g. kitty, ghostty, WezTerm, foot). Ctrl+B is
    # tmux's default prefix key — it would silently fail to reach the editor
    # in common setups. Alt+B was also ruled out: Textual's legacy ANSI
    # parser hard-codes the ESC-b byte sequence to "ctrl+left" (cursor word
    # left) on terminals without the Kitty keyboard protocol, so a
    # Binding("alt+b", ...) would silently never fire there either. Alt+G
    # and Alt+I are not shadowed by any such hard-coded legacy mapping, but
    # they still need priority=True: on those same legacy terminals, an
    # Alt+letter keystroke is reported as a Key event with a printable
    # `character` set (e.g. Alt+G -> character="g"), and TextArea's own key
    # handling treats any printable character as literal text input,
    # inserting it and calling event.stop()/prevent_default() before the
    # event ever reaches normal (non-priority) binding resolution. Marking
    # these two bindings priority=True makes Textual check them ahead of the
    # focused widget's own key handling, so they fire correctly instead of
    # destroying the selection and inserting a literal "g"/"i".
    BINDINGS = [
        Binding("ctrl+s", "save", "저장"),
        Binding("alt+g", "toggle_bold", "굵게", priority=True),
        Binding("alt+i", "toggle_italic", "기울임", priority=True),
    ]

    class Saved(Message):
        def __init__(self, path: str) -> None:
            super().__init__()
            self.path = path

    class Modified(Message):
        pass

    class SaveRequested(Message):
        """Request a destination for a document that has no path yet."""

    class SaveFailed(Message):
        def __init__(self, error: EditorFileError) -> None:
            super().__init__()
            self.error = error

    def __init__(self, **kwargs) -> None:
        super().__init__("", show_line_numbers=True, **kwargs)
        self.current_path: str | None = None
        self._autosave_timer: Timer | None = None
        self._saved_text: str = ""  # text at last save/open

    def on_mount(self) -> None:
        self.register_theme(_make_theme())
        self.theme = "tmd-dark"

    def on_unmount(self) -> None:
        self._cancel_autosave()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open_file(self, path: str) -> None:
        """Load *path* into the editor and record it in history."""
        if self.is_dirty:
            raise UnsavedChangesError("Resolve the current document before opening another")

        target = Path(path).expanduser().resolve()
        try:
            content = target.read_text(encoding="utf-8")
        except (OSError, UnicodeError) as error:
            raise EditorFileError("Open", str(target), error) from error

        self._cancel_autosave()
        self.load_text(content)
        self.current_path = str(target)
        self._saved_text = content
        add_to_history(str(target))

    def save_file(self, path: str | None = None) -> bool:
        """Atomically write the current buffer, optionally assigning a new path."""
        destination = path or self.current_path
        if destination is None:
            return False

        target = Path(destination).expanduser().resolve()
        self._cancel_autosave()
        self._write_text(target, self.text)
        self.current_path = str(target)
        self._saved_text = self.text
        add_to_history(str(target))
        self.post_message(self.Saved(path=str(target)))
        return True

    def new_document(self) -> None:
        """Reset the editor after the caller has resolved pending changes."""
        if self.is_dirty:
            raise UnsavedChangesError("Resolve the current document before creating another")
        self._cancel_autosave()
        self.current_path = None
        self._saved_text = ""
        self.load_text("")

    def discard_changes(self) -> None:
        """Mark the current buffer resolved without writing it."""
        self._cancel_autosave()
        self._saved_text = self.text

    @property
    def is_dirty(self) -> bool:
        return self.text != self._saved_text

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------

    def _build_highlight_map(self) -> None:
        """Override to inject annotate_line spans into the highlight map."""
        self._line_cache.clear()
        self._highlights.clear()
        for i, spans in enumerate(annotate_document(self.text)):
            for start, end, style_str in spans:
                self._highlights[i].append((start, end, style_str))

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if self.text == self._saved_text:
            return  # ignore spurious change on load or after save
        self.post_message(self.Modified())
        self._schedule_autosave()

    # ------------------------------------------------------------------
    # Actions (bound via BINDINGS)
    # ------------------------------------------------------------------

    def action_save(self) -> None:
        if self.current_path is None:
            self.post_message(self.SaveRequested())
            return
        try:
            self.save_file()
        except EditorFileError as error:
            self.post_message(self.SaveFailed(error))

    def action_toggle_bold(self) -> None:
        self._wrap_selection("**", "**")

    def action_toggle_italic(self) -> None:
        self._wrap_selection("*", "*")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _schedule_autosave(self) -> None:
        """Debounced autosave: reset the 2-second countdown on every change."""
        self._cancel_autosave()
        if self.current_path is not None:
            expected_path = self.current_path
            self._autosave_timer = self.set_timer(
                _AUTOSAVE_DELAY,
                lambda: self._autosave(expected_path),
            )

    def _cancel_autosave(self) -> None:
        if self._autosave_timer is not None:
            self._autosave_timer.stop()
            self._autosave_timer = None

    def _autosave(self, expected_path: str) -> None:
        self._autosave_timer = None
        if self.current_path != expected_path or not self.is_dirty:
            return
        try:
            self.save_file()
        except EditorFileError as error:
            self.post_message(self.SaveFailed(error))

    @staticmethod
    def _write_text(path: Path, content: str) -> None:
        """Write through a sibling temporary file and replace atomically."""
        try:
            existing_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
            fd, temporary_name = tempfile.mkstemp(
                prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
            )
            temporary_path = Path(temporary_name)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as file:
                    file.write(content)
                    file.flush()
                    os.fsync(file.fileno())
                if existing_mode is not None:
                    temporary_path.chmod(existing_mode)
                os.replace(temporary_path, path)
            finally:
                temporary_path.unlink(missing_ok=True)
        except OSError as error:
            raise EditorFileError("Save", str(path), error) from error

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
