from tmd_cli.preview import render_fragment, render_page


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
