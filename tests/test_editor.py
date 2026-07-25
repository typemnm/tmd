
import pytest
from textual import events
from textual.app import App, ComposeResult

from tmd_cli.editor import MarkdownEditor


class EditorApp(App):
    def compose(self) -> ComposeResult:
        yield MarkdownEditor()


@pytest.mark.asyncio
async def test_open_file(tmp_path):
    md_file = tmp_path / "test.md"
    md_file.write_text("# Hello\n\nWorld", encoding="utf-8")
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.open_file(str(md_file))
        assert editor.current_path == str(md_file)
        assert "Hello" in editor.text


@pytest.mark.asyncio
async def test_save_file(tmp_path):
    md_file = tmp_path / "save_test.md"
    md_file.write_text("original", encoding="utf-8")
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.open_file(str(md_file))
        await pilot.press("end")
        await pilot.press("space", "e", "d", "i", "t", "e", "d")
        editor.save_file()
        assert "edited" in md_file.read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_current_path_none_initially():
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        assert editor.current_path is None


@pytest.mark.asyncio
async def test_save_file_no_path_does_nothing(tmp_path):
    """save_file() with no current_path must not raise."""
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        assert editor.current_path is None
        editor.save_file()  # should be a no-op


@pytest.mark.asyncio
async def test_saved_message_posted(tmp_path):
    """save_file() posts a Saved message with the correct path."""
    md_file = tmp_path / "msg_test.md"
    md_file.write_text("content", encoding="utf-8")
    messages: list[MarkdownEditor.Saved] = []

    class MsgApp(App):
        def compose(self) -> ComposeResult:
            yield MarkdownEditor()

        def on_markdown_editor_saved(self, event: MarkdownEditor.Saved) -> None:
            messages.append(event)

    async with MsgApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.open_file(str(md_file))
        editor.save_file()
        await pilot.pause()
        assert len(messages) == 1
        assert messages[0].path == str(md_file)


@pytest.mark.asyncio
async def test_modified_message_posted(tmp_path):
    """Typing text posts a Modified message."""
    messages: list[MarkdownEditor.Modified] = []

    class MsgApp(App):
        def compose(self) -> ComposeResult:
            yield MarkdownEditor()

        def on_markdown_editor_modified(self, event: MarkdownEditor.Modified) -> None:
            messages.append(event)

    async with MsgApp().run_test() as pilot:
        await pilot.press("h", "e", "l", "l", "o")
        await pilot.pause()
        assert len(messages) >= 1


@pytest.mark.asyncio
async def test_bindings_present():
    """BINDINGS must include ctrl+s, alt+g, alt+i, and must NOT include the
    old ctrl+b/ctrl+i/alt+b bindings. On terminals without the Kitty
    keyboard protocol (most terminals), ctrl+i is unreachable because that
    keystroke is reported as "tab", which Textual's BINDINGS matching
    treats as a plain, literal "tab" event — never "ctrl+i" — and ctrl+b
    collides with tmux's default prefix key. alt+b was also tried and
    dropped: Textual's legacy ANSI parser hard-codes that byte sequence to
    "ctrl+left" on terminals without the Kitty protocol, so the binding
    never fired there either. bold/italic use alt+g/alt+i instead, neither
    of which is shadowed by a hard-coded legacy mapping. This is a
    code-level regression lock: it fails if the old bindings are ever
    re-added."""
    binding_keys = {b.key for b in MarkdownEditor.BINDINGS}
    assert "ctrl+s" in binding_keys
    assert "alt+g" in binding_keys
    assert "alt+i" in binding_keys
    assert "ctrl+b" not in binding_keys
    assert "ctrl+i" not in binding_keys
    assert "alt+b" not in binding_keys


@pytest.mark.asyncio
async def test_annotate_line_applied(tmp_path):
    """annotate_line spans must be visible in the editor without error."""
    md_file = tmp_path / "styled.md"
    md_file.write_text("# Heading", encoding="utf-8")
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.open_file(str(md_file))
        await pilot.pause()
        # _build_highlight_map must produce spans for the heading line
        editor._build_highlight_map()
        assert 0 in editor._highlights  # line 0 "# Heading" should have a span
        # The style string for H1 should be in the first highlight
        styles_on_line0 = [h[2] for h in editor._highlights[0]]
        assert any("cyan" in s or "bold" in s for s in styles_on_line0)


@pytest.mark.asyncio
async def test_alt_g_toggles_bold_via_keypress():
    """Pressing alt+g with a selection wraps it in ** (the actual key path,
    not just action_toggle_bold called directly)."""
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.focus()
        editor.load_text("hello world")
        await pilot.pause()
        editor.selection = editor.selection.__class__((0, 0), (0, 5))
        await pilot.press("alt+g")
        await pilot.pause()
        assert "**hello**" in editor.text


@pytest.mark.asyncio
async def test_alt_i_toggles_italic_via_keypress():
    """Pressing alt+i with a selection wraps it in * (the actual key path,
    not just action_toggle_italic called directly) — the real keyboard
    shortcut for italic now that ctrl+i is unreachable on terminals without
    the Kitty keyboard protocol (see test_bindings_present)."""
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.focus()
        editor.load_text("hello world")
        await pilot.pause()
        editor.selection = editor.selection.__class__((0, 0), (0, 5))
        await pilot.press("alt+i")
        await pilot.pause()
        assert "*hello*" in editor.text


async def _send_legacy_terminal_alt_key(pilot, key: str, character: str) -> None:
    """Dispatch a Key event the way a real terminal's legacy ANSI parser
    would for an Alt+<letter> keystroke — with `character` explicitly set.

    `pilot.press()` cannot reproduce this: Textual's own `_press_keys` only
    sets `character` for single-character key names, so for a multi-char
    name like "alt+g" it synthesizes `character=None`. That gap is exactly
    why the priority=True regression above survived Pilot-based tests: real
    terminals report `Key(key="alt+g", character="g")`, and without
    priority=True, TextArea's own key handling swallows any printable
    character as literal text before normal bindings are ever consulted.

    This helper goes through the same path a real driver uses
    (`driver.send_message` -> `App._post_message` -> `App.on_event`), so it
    also exercises the priority-binding check in `App.on_event`, not just
    the widget's action method.
    """
    app = pilot.app
    driver = app._driver
    assert driver is not None
    key_event = events.Key(key, character)
    key_event.set_sender(app)
    driver.send_message(key_event)
    await pilot.pause()
    await pilot.pause()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key", "character", "wrapped"),
    [
        ("alt+g", "g", "**hello**"),
        ("alt+i", "i", "*hello*"),
    ],
)
async def test_alt_key_toggles_formatting_on_legacy_terminal(key, character, wrapped):
    """Regression test: on a real terminal without the Kitty keyboard
    protocol, Alt+G/Alt+I key events carry a printable `character` field.
    Without priority=True on these bindings, TextArea's own key handling
    would consume that character as literal text input (destroying the
    selection and inserting "g"/"i") before the binding is ever considered.
    This must actually toggle bold/italic instead."""
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.focus()
        editor.load_text("hello world")
        await pilot.pause()
        editor.selection = editor.selection.__class__((0, 0), (0, 5))
        await _send_legacy_terminal_alt_key(pilot, key, character)
        assert wrapped in editor.text
        # The literal character must NOT have been inserted as plain text
        # in place of the selection (the pre-fix, buggy behavior).
        assert editor.text.count(character) == wrapped.count(character)


@pytest.mark.asyncio
async def test_open_file_does_not_post_modified(tmp_path):
    """open_file() must not post a Modified message even though TextArea.Changed fires."""
    md_file = tmp_path / "no_modified.md"
    md_file.write_text("# No Spurious Modified", encoding="utf-8")
    messages: list[MarkdownEditor.Modified] = []

    class MsgApp(App):
        def compose(self) -> ComposeResult:
            yield MarkdownEditor()

        def on_markdown_editor_modified(self, event: MarkdownEditor.Modified) -> None:
            messages.append(event)

    async with MsgApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.open_file(str(md_file))
        await pilot.pause()
        await pilot.pause()
        assert len(messages) == 0
