import json

import pytest
from textual.app import App, ComposeResult

from tmd_cli.app import TmdApp, UnsavedDialog
from tmd_cli.editor import MarkdownEditor, UnsavedChangesError
from tmd_cli.history import add_to_history, get_history
from tmd_cli.markdown import annotate_document, annotate_line


class EditorApp(App):
    def compose(self) -> ComposeResult:
        yield MarkdownEditor()


def test_malformed_history_entries_are_ignored(tmp_path, monkeypatch):
    history = tmp_path / ".tmd_history"
    valid_file = tmp_path / "valid.md"
    valid_file.touch()
    history.write_text(
        json.dumps([
            None,
            {"path": 3, "last_opened": "now"},
            {"path": str(valid_file)},
            {"path": str(valid_file), "last_opened": "now"},
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr("tmd_cli.history.HISTORY_FILE", history)

    assert get_history() == [{"path": str(valid_file), "last_opened": "now"}]


def test_history_write_failure_is_non_fatal(tmp_path, monkeypatch):
    note = tmp_path / "note.md"
    note.touch()

    def fail(_entries):
        raise OSError("read-only")

    monkeypatch.setattr("tmd_cli.history._save", fail)
    add_to_history(str(note))


@pytest.mark.asyncio
async def test_dirty_document_cannot_be_replaced(tmp_path):
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("first", encoding="utf-8")
    second.write_text("second", encoding="utf-8")

    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.open_file(str(first))
        editor.load_text("changed")
        with pytest.raises(UnsavedChangesError):
            editor.open_file(str(second))

    assert first.read_text(encoding="utf-8") == "first"


@pytest.mark.asyncio
async def test_save_as_assigns_path_and_cleans_temp_files(tmp_path):
    destination = tmp_path / "new.md"
    async with EditorApp().run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.load_text("# New")
        assert editor.save_file(str(destination))
        assert editor.current_path == str(destination.resolve())
        assert not editor.is_dirty

    assert destination.read_text(encoding="utf-8") == "# New"
    assert list(tmp_path.glob(".new.md.*.tmp")) == []


@pytest.mark.asyncio
async def test_existing_document_is_saved_before_new(tmp_path):
    note = tmp_path / "note.md"
    note.write_text("old", encoding="utf-8")

    async with TmdApp(initial_path=str(note), root=str(tmp_path)).run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.load_text("changed")
        await pilot.press("ctrl+n")
        await pilot.pause()
        assert editor.text == ""
        assert editor.current_path is None

    assert note.read_text(encoding="utf-8") == "changed"


@pytest.mark.asyncio
async def test_untitled_document_prompts_before_discard(tmp_path):
    async with TmdApp(root=str(tmp_path)).run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.load_text("not saved")
        await pilot.press("ctrl+n")
        await pilot.pause()
        assert isinstance(pilot.app.screen, UnsavedDialog)
        assert editor.text == "not saved"


def test_fenced_code_block_has_document_level_style():
    lines = annotate_document("```python\n**literal**\n```")
    assert all(any("grey" in style for _, _, style in spans) for spans in lines)


def test_inline_code_protects_nested_markers():
    spans = annotate_line("`**literal**`")
    assert len(spans) == 1
    assert "grey" in spans[0][2]

@pytest.mark.asyncio
async def test_find_selects_the_next_match(tmp_path):
    async with TmdApp(root=str(tmp_path)).run_test() as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        editor.load_text("alpha needle omega")
        pilot.app._find_text("needle")
        await pilot.pause()
        assert editor.selected_text == "needle"
