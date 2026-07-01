import pytest
from pathlib import Path

from tmd.app import TmdApp, StatusBar
from tmd.editor import MarkdownEditor
from tmd.sidebar import Sidebar


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
