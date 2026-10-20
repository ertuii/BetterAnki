"""Local HTTP server: serves the UI, collection media, and an RPC endpoint for the MCP proxy.

Bound to 127.0.0.1 only. /rpc needs the token from server.json (custom header -> browsers can't forge it cross-origin).
"""

import json
import secrets
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

from .core import Core, data_dir

WEB_DIR = Path(__file__).parent / "web"
INFO_FILE = data_dir() / "server.json"


class Handler(SimpleHTTPRequestHandler):
    core: Core
    token: str

    def log_message(self, *a):
        pass

    def translate_path(self, path):
        path = unquote(path.split("?", 1)[0])
        web = super().translate_path(path)
        if not path.startswith("/media/") and Path(web).exists():
            return web
        # media files: /media/x.jpg (cards) or /x.jpg (relative <img> in the editor)
        media = Path(self.core.media_dir()).resolve()
        target = (media / path.removeprefix("/media/").lstrip("/")).resolve()
        return str(target) if target.is_relative_to(media) else ""

    def _foreign_host(self) -> bool:
        """DNS rebinding: a website whose name suddenly resolves to 127.0.0.1 sends its own name as Host."""
        port = self.server.server_address[1]
        if self.headers.get("Host") in (f"127.0.0.1:{port}", f"localhost:{port}"):
            return False
        self.send_error(403)
        return True

    def do_GET(self):
        if not self._foreign_host():
            super().do_GET()

    def do_HEAD(self):
        if not self._foreign_host():
            super().do_HEAD()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        if self.path.startswith("/katex/"):  # fonts for formulas, fetched from the sandboxed card frame (origin "null")
            self.send_header("Access-Control-Allow-Origin", "*")
        super().end_headers()

    def do_POST(self):
        if self._foreign_host():
            return
        if self.path != "/rpc" or not secrets.compare_digest(self.headers.get("X-Token", ""), self.token):
            self.send_error(403)
            return
        req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        method = req["method"]
        try:
            if method.startswith("_") or method.startswith("pick_"):
                raise ValueError(f"not allowed: {method}")
            body = {"result": getattr(self.core, method)(**req.get("args", {}))}
            try:  # /rpc is Claude (MCP): show its changes, e.g. new cards in the inbox, right away
                self.core._window and self.core._window.evaluate_js(f"window.__baRefresh && window.__baRefresh({json.dumps(method)})")
            except Exception:
                pass  # window closing; the result still counts
        except Exception as e:
            body = {"error": f"{type(e).__name__}: {e}"}
        data = json.dumps(body).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def start(core: Core) -> str:
    token = secrets.token_urlsafe(32)
    handler = type("H", (Handler,), {"core": core, "token": token})
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), partial(handler, directory=str(WEB_DIR)))
    port = httpd.server_address[1]
    INFO_FILE.write_text(json.dumps({"port": port, "token": token}))
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/"


def stop():
    INFO_FILE.unlink(missing_ok=True)
