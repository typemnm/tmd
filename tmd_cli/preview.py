from __future__ import annotations

import html

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

_md = MarkdownIt("gfm-like").use(tasklists_plugin)

PAGE_CSS = """
:root { color-scheme: light dark; }
body {
  margin: 0;
  background: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 16px;
  line-height: 1.7;
  color: #2b2b2b;
}
#content { max-width: 680px; margin: 0 auto; padding: 40px 44px; }
h1 { font-size: 1.9em; font-weight: 800; margin: 0 0 0.5em; padding-bottom: 0.3em; border-bottom: 2px solid #1a1a1a; letter-spacing: -0.01em; }
h2 { font-size: 1.3em; font-weight: 700; margin: 1.3em 0 0.4em; color: #1a1a1a; }
h3, h4, h5, h6 { font-weight: 700; margin: 1.1em 0 0.35em; }
p { margin: 0.5em 0; }
ul, ol { margin: 0.5em 0; padding-left: 1.4em; }
li { margin: 0.15em 0; }
.contains-task-list { list-style: none; padding-left: 0; }
.task-list-item { display: flex; gap: 0.5em; align-items: flex-start; padding: 2px 0; }
.task-list-item-checkbox { margin-top: 6px; accent-color: #2383e2; }
blockquote { margin: 0.6em 0; padding: 0.4em 0 0.4em 1em; background: #f4f1ea; border-left: 4px solid #b8a97a; font-style: italic; }
code { background: #eee; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.85em; font-family: "SFMono-Regular", Menlo, Consolas, monospace; }
pre { background: #1e1e1e; color: #e6e6e6; border-radius: 6px; padding: 14px 16px; overflow-x: auto; }
pre code { background: none; padding: 0; color: inherit; }
table { border-collapse: collapse; margin: 0.6em 0; font-size: 0.95em; width: 100%; }
th, td { border-bottom: 1px solid #ddd; padding: 8px 10px; text-align: left; }
th { border-bottom: 2px solid #1a1a1a; font-weight: 700; }
hr { border: none; border-top: 1px solid #ccc; margin: 1.5em 0; }
a { color: #2383e2; }

@media (prefers-color-scheme: dark) {
  body { background: #191919; color: #d4d4d4; }
  h1 { border-bottom-color: #444; }
  h2 { color: #e8e8e8; }
  blockquote { background: #2a2721; border-left-color: #8a7a4f; }
  code { background: #2e2e2e; }
  th, td { border-bottom-color: #3a3a3a; }
  th { border-bottom-color: #555; }
  hr { border-top-color: #3a3a3a; }
  a { color: #6cb2f5; }
}
"""


def render_fragment(text: str) -> str:
    """Render Markdown body text to an HTML fragment (no <html>/<body> wrapper)."""
    try:
        return _md.render(text)
    except Exception:
        return f"<pre>{html.escape(text)}</pre>"


def render_page(text: str, title: str) -> str:
    """Render a full standalone HTML page that live-updates via /events (SSE)."""
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<title>{html.escape(title)}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<div id="content">{render_fragment(text)}</div>
<script>
const source = new EventSource("/events");
source.onmessage = (event) => {{
  document.getElementById("content").innerHTML = event.data;
}};
</script>
</body>
</html>
"""
