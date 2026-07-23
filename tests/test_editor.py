
import pytest
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
    """BINDINGS must include ctrl+s, ctrl+b, ctrl+i."""
    binding_keys = {b.key for b in MarkdownEditor.BINDINGS}
    assert "ctrl+s" in binding_keys
    assert "ctrl+b" in binding_keys
    assert "ctrl+i" in binding_keys


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
