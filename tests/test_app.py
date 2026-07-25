
import asyncio
import urllib.request

import pytest

from tmd_cli.app import StatusBar, TmdApp
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
