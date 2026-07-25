import time
import urllib.request

import pytest

from tmd_cli.preview import PreviewServer, render_fragment, render_page


def test_render_fragment_heading_and_emphasis():
    html = render_fragment("# Title\n\n**bold** and *italic*")
    assert "<h1>Title</h1>" in html
    assert "<strong>bold</strong>" in html
    assert "<em>italic</em>" in html


def test_render_fragment_table():
    html = render_fragment("| a | b |\n|---|---|\n| 1 | 2 |\n")
    assert "<table>" in html
    assert "<th>a</th>" in html
    assert "<td>1</td>" in html


def test_render_fragment_task_list_checkboxes():
    html = render_fragment("- [x] done\n- [ ] todo\n")
    assert '<input class="task-list-item-checkbox" checked="checked" disabled="disabled" type="checkbox">' in html
    assert '<input class="task-list-item-checkbox" disabled="disabled" type="checkbox">' in html


def test_render_fragment_code_fence():
    html = render_fragment("```python\ndef f():\n    pass\n```\n")
    assert "<pre><code" in html
    assert "def f():" in html


def test_render_fragment_never_raises_on_arbitrary_text():
    # Malformed/edge-case input must degrade gracefully, never throw.
    html = render_fragment("<script>alert(1)</script>\n\x00﻿")
    assert isinstance(html, str)


def test_render_page_embeds_fragment_and_title():
    page = render_page("# Hello", title="notes.md")
    assert "<title>notes.md</title>" in page
    assert "<h1>Hello</h1>" in page
    assert 'id="content"' in page
    assert "EventSource" in page


def test_render_page_escapes_title():
    page = render_page("text", title="<b>evil</b>")
    assert "<title>&lt;b&gt;evil&lt;/b&gt;</title>" in page


def _wait_for_clients(server: PreviewServer, count: int = 1, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(server._httpd.clients) >= count:  # noqa: SLF001 - test-only introspection
            return
        time.sleep(0.01)
    raise AssertionError("timed out waiting for SSE client to register")


def test_preview_server_serves_index():
    server = PreviewServer(get_text=lambda: "# Hi", title="hi.md")
    url = server.start()
    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            assert response.status == 200
            body = response.read().decode("utf-8")
            assert "<h1>Hi</h1>" in body
            assert "<title>hi.md</title>" in body
    finally:
        server.stop()


def test_preview_server_pushes_updates_over_sse():
    state = {"text": "first"}
    server = PreviewServer(get_text=lambda: state["text"])
    url = server.start()
    try:
        events = urllib.request.urlopen(url + "events", timeout=5)
        try:
            _wait_for_clients(server)
            state["text"] = "second"
            server.publish(state["text"])
            line = events.readline().decode("utf-8")
            assert line.startswith("data: ")
            assert "second" in line
        finally:
            events.close()
    finally:
        server.stop()


def test_preview_server_stop_releases_port():
    server = PreviewServer(get_text=lambda: "")
    url = server.start()
    server.stop()
    with pytest.raises(OSError):
        urllib.request.urlopen(url, timeout=1)
