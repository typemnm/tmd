
import asyncio
import urllib.request

import pytest
from textual.widgets import Input

from tmd_cli.app import PathDialog, StatusBar, TmdApp, main
from tmd_cli.editor import MarkdownEditor
from tmd_cli.sidebar import Sidebar


@pytest.mark.asyncio
async def test_app_launches_without_file():
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        assert pilot.app is not None


@pytest.mark.asyncio
async def test_app_opens_file(tmp_path):
    md = tmp_path / "hello.md"
    md.write_text("# Hello World", encoding="utf-8")
    async with TmdApp(initial_path=str(md)).run_test(size=(120, 40)) as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        assert "Hello World" in editor.text


@pytest.mark.asyncio
async def test_ctrl_q_exits():
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+q")
        # app should have exited after ctrl+q
        assert not pilot.app.is_running


@pytest.mark.asyncio
async def test_status_idle_on_start():
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        status = pilot.app.query_one(StatusBar)
        content = str(status.content)
        assert "tmd" in content.lower() or "Terminal Markdown Editor" in content


@pytest.mark.asyncio
async def test_sidebar_file_selection_opens_file(tmp_path):
    md = tmp_path / "selected.md"
    md.write_text("# Selected File Content", encoding="utf-8")
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        pilot.app.post_message(Sidebar.FileSelected(path=str(md)))
        await pilot.pause()
        editor = pilot.app.query_one(MarkdownEditor)
        assert "Selected File Content" in editor.text


@pytest.mark.asyncio
async def test_action_new_file():
    """Ctrl+N clears the editor."""
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        editor = pilot.app.query_one(MarkdownEditor)
        # Load some text first
        editor.load_text("some content")
        await pilot.press("ctrl+n")
        await pilot.pause()
        assert editor.text == "" or editor.current_path is None


@pytest.mark.asyncio
async def test_action_toggle_sidebar():
    """Ctrl+\\ hides and shows the sidebar."""
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        sidebar = pilot.app.query_one(Sidebar)
        initial_display = sidebar.display
        await pilot.press("ctrl+backslash")
        await pilot.pause()
        assert sidebar.display != initial_display


@pytest.mark.asyncio
async def test_modified_updates_status_bar(tmp_path):
    """Typing in editor updates status bar to unsaved."""
    md = tmp_path / "m.md"
    md.write_text("hello", encoding="utf-8")
    async with TmdApp(initial_path=str(md)).run_test(size=(120, 40)) as pilot:
        status = pilot.app.query_one(StatusBar)
        editor = pilot.app.query_one(MarkdownEditor)
        editor.focus()
        await pilot.pause()
        await pilot.press("end", "x")
        await pilot.pause()
        await pilot.pause()
        assert "미저장" in str(status.content) or "○" in str(status.content)


@pytest.mark.asyncio
async def test_action_toggle_preview(monkeypatch, tmp_path):
    monkeypatch.setattr("tmd_cli.app.webbrowser.open", lambda url: None)
    md = tmp_path / "p.md"
    md.write_text("# Hi", encoding="utf-8")
    async with TmdApp(initial_path=str(md)).run_test(size=(120, 40)) as pilot:
        assert pilot.app._preview is None
        await pilot.press("ctrl+p")
        await pilot.pause()
        assert pilot.app._preview is not None

        await pilot.press("ctrl+p")
        await pilot.pause()
        assert pilot.app._preview is None


@pytest.mark.asyncio
async def test_typing_publishes_to_preview_after_debounce(monkeypatch, tmp_path):
    monkeypatch.setattr("tmd_cli.app.webbrowser.open", lambda url: None)
    md = tmp_path / "p.md"
    md.write_text("hello", encoding="utf-8")
    async with TmdApp(initial_path=str(md)).run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+p")
        await pilot.pause()

        published: list[str] = []
        pilot.app._preview.publish = published.append

        editor = pilot.app.query_one(MarkdownEditor)
        editor.focus()
        await pilot.pause()
        await pilot.press("end", "!")
        await pilot.pause()
        await asyncio.sleep(0.35)
        await pilot.pause()

        assert published
        assert published[-1] == "hello!"


@pytest.mark.asyncio
async def test_find_dialog_has_no_path_suggester():
    """Ctrl+F's search dialog must not get path autocomplete — accepting a
    ghost-text suggestion there would silently replace the search query."""
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+f")
        await pilot.pause()
        dialog = pilot.app.screen
        assert isinstance(dialog, PathDialog)
        path_input = dialog.query_one("#path", Input)
        assert path_input.suggester is None
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_open_file_dialog_has_path_suggester():
    """Ctrl+O's file-open dialog should keep its path autocomplete."""
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+o")
        await pilot.pause()
        dialog = pilot.app.screen
        assert isinstance(dialog, PathDialog)
        path_input = dialog.query_one("#path", Input)
        assert path_input.suggester is not None
        await pilot.press("escape")


@pytest.mark.asyncio
async def test_open_dialog_enter_with_unresolvable_tilde_user_does_not_crash():
    """Pressing Enter on an unresolvable "~someuser" (bypassing/ignoring the
    autocomplete suggestion, which is separately hardened) must not crash
    the app. Path(path).expanduser() raises RuntimeError for a tilde token
    with no matching passwd entry — the same mechanism PathSuggester was
    hardened against — but action_open_file_dialog's open_path() closure
    calls it directly and unguarded, so submitting via Enter reached the
    exact same crash through a different path."""
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+o")
        await pilot.pause()
        dialog = pilot.app.screen
        assert isinstance(dialog, PathDialog)
        path_input = dialog.query_one("#path", Input)
        path_input.value = "~this-user-does-not-exist-xyz"
        await pilot.press("enter")
        await pilot.pause()

        assert pilot.app.is_running
        assert any(
            n.severity == "error" for n in pilot.app._notifications
        )


@pytest.mark.asyncio
async def test_save_as_enter_with_unresolvable_tilde_user_does_not_crash():
    """Same crash, reached via the save-as dialog's selected() closure,
    which calls Path(path).expanduser().resolve() directly and unguarded."""
    async with TmdApp().run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+shift+s")
        await pilot.pause()
        dialog = pilot.app.screen
        assert isinstance(dialog, PathDialog)
        path_input = dialog.query_one("#path", Input)
        path_input.value = "~this-user-does-not-exist-xyz/out.md"
        await pilot.press("enter")
        await pilot.pause()

        assert pilot.app.is_running
        assert any(
            n.severity == "error" for n in pilot.app._notifications
        )


def test_main_with_unresolvable_tilde_user_path_exits_cleanly(monkeypatch, capsys):
    """main()'s CLI argument path is the last unguarded spot with this crash
    class: Path(args.path).expanduser().resolve() raises RuntimeError for an
    unresolvable "~someuser" token (no matching passwd entry), the same
    mechanism PathSuggester and the open/save-as dialogs were hardened
    against. It must be caught and turned into the same clean
    parser.error(...) used for the "neither file nor directory" case, not
    let propagate as a raw traceback."""
    monkeypatch.setattr(
        "sys.argv", ["tmd", "~this-user-does-not-exist-xyz/out.md"]
    )
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    assert "File or directory not found" in captured.err


@pytest.mark.asyncio
async def test_preview_stops_on_unmount(monkeypatch, tmp_path):
    monkeypatch.setattr("tmd_cli.app.webbrowser.open", lambda url: None)
    md = tmp_path / "p.md"
    md.write_text("# Hi", encoding="utf-8")
    async with TmdApp(initial_path=str(md)).run_test(size=(120, 40)) as pilot:
        await pilot.press("ctrl+p")
        await pilot.pause()
        server = pilot.app._preview
        assert server is not None
        port = server.port  # capture before unmount stops the server

    # After the app context exits, App.on_unmount must have stopped the server.
    with pytest.raises(OSError):
        urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
