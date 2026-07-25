from __future__ import annotations

import html
import queue
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from markdown_it import MarkdownIt
from mdit_py_plugins.tasklists import tasklists_plugin

_md = MarkdownIt("gfm-like", {"html": False}).use(tasklists_plugin)

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
h1 {
  font-size: 1.9em; font-weight: 800; margin: 0 0 0.5em;
  padding-bottom: 0.3em; border-bottom: 2px solid #1a1a1a; letter-spacing: -0.01em;
}
h2 { font-size: 1.3em; font-weight: 700; margin: 1.3em 0 0.4em; color: #1a1a1a; }
h3, h4, h5, h6 { font-weight: 700; margin: 1.1em 0 0.35em; }
p { margin: 0.5em 0; }
ul, ol { margin: 0.5em 0; padding-left: 1.4em; }
li { margin: 0.15em 0; }
.contains-task-list { list-style: none; padding-left: 0; }
.task-list-item { display: flex; gap: 0.5em; align-items: flex-start; padding: 2px 0; }
.task-list-item-checkbox { margin-top: 6px; accent-color: #2383e2; }
blockquote {
  margin: 0.6em 0; padding: 0.4em 0 0.4em 1em;
  background: #f4f1ea; border-left: 4px solid #b8a97a; font-style: italic;
}
code {
  background: #eee; padding: 0.15em 0.4em; border-radius: 4px; font-size: 0.85em;
  font-family: "SFMono-Regular", Menlo, Consolas, monospace;
}
pre {
  background: #1e1e1e; color: #e6e6e6; border-radius: 6px;
  padding: 14px 16px; overflow-x: auto;
}
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


def _format_sse_event(data: str) -> bytes:
    """Encode *data* as a single SSE event, preserving embedded newlines."""
    payload = "\n".join(f"data: {line}" for line in data.split("\n"))
    return f"{payload}\n\n".encode()


class _PreviewHTTPServer(ThreadingHTTPServer):
    daemon_threads = True

    def __init__(self, server_address, handler_cls, get_text, title) -> None:
        super().__init__(server_address, handler_cls)
        self.get_text: Callable[[], str] = get_text
        self.title = title
        self.clients: list[queue.Queue[str | None]] = []
        self.clients_lock = threading.Lock()
        self.stopping = False

    def add_client(self, client_queue: queue.Queue[str | None]) -> bool:
        with self.clients_lock:
            if self.stopping:
                return False
            self.clients.append(client_queue)
            return True

    def remove_client(self, client_queue: queue.Queue[str | None]) -> None:
        with self.clients_lock:
            if client_queue in self.clients:
                self.clients.remove(client_queue)

    def publish(self, text: str) -> None:
        fragment = render_fragment(text)
        with self.clients_lock:
            clients = list(self.clients)
        for client_queue in clients:
            client_queue.put(fragment)

    def close_all_clients(self) -> None:
        with self.clients_lock:
            self.stopping = True
            clients = list(self.clients)
        for client_queue in clients:
            client_queue.put(None)

    def handle_error(self, request, client_address) -> None:
        # Best-effort preview server; never write tracebacks to the terminal
        # Textual owns (BaseHTTPRequestHandler.handle_error defaults to stderr,
        # which corrupts the TUI's escape-sequence stream).
        pass


class _PreviewHandler(BaseHTTPRequestHandler):
    server: _PreviewHTTPServer

    def log_message(self, format: str, *args) -> None:  # noqa: A002 - stdlib signature
        pass  # silence default access logging to stdout

    def do_GET(self) -> None:
        expected_host = f"127.0.0.1:{self.server.server_address[1]}"
        if self.headers.get("Host") != expected_host:
            self.send_response(403)
            self.end_headers()
            return
        if self.path == "/":
            self._serve_index()
        elif self.path == "/events":
            self._serve_events()
        else:
            self.send_response(404)
            self.end_headers()

    def _serve_index(self) -> None:
        body = render_page(self.server.get_text(), self.server.title).encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def _serve_events(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        client_queue: queue.Queue[str | None] = queue.Queue()
        if not self.server.add_client(client_queue):
            return
        try:
            while True:
                fragment = client_queue.get()
                if fragment is None:
                    break
                self.wfile.write(_format_sse_event(fragment))
                self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        finally:
            self.server.remove_client(client_queue)


class PreviewServer:
    """Read-only, live-updating HTML preview of a single Markdown buffer."""

    def __init__(self, get_text: Callable[[], str], title: str = "tmd preview") -> None:
        self._get_text = get_text
        self._title = title
        self._httpd: _PreviewHTTPServer | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> str:
        self._httpd = _PreviewHTTPServer(
            ("127.0.0.1", 0), _PreviewHandler, self._get_text, self._title
        )
        self._thread = threading.Thread(
            target=self._httpd.serve_forever, kwargs={"poll_interval": 0.05}, daemon=True
        )
        self._thread.start()
        port = self._httpd.server_address[1]
        return f"http://127.0.0.1:{port}/"

    def publish(self, text: str) -> None:
        if self._httpd is not None:
            self._httpd.publish(text)

    @property
    def port(self) -> int | None:
        return None if self._httpd is None else self._httpd.server_address[1]

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.close_all_clients()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2)
            self._thread = None
