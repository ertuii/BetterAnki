import json

import webview
from webview.dom import DOMEventHandler

from . import claude_connect, server
from .core import Core


def _bind(window):
    """Runs once the window is up: file drag & drop and keeping Claude's paths current."""

    def on_drop(e):
        # pywebview only hands out real file paths to Python-side drop handlers
        paths = [f.get("pywebviewFullPath") for f in e.get("dataTransfer", {}).get("files", [])]
        if paths := [p for p in paths if p]:
            window.evaluate_js(f"window.__baImport && window.__baImport({json.dumps(paths[0])})")

    window.dom.document.events.dragover += DOMEventHandler(lambda e: None, True, True, debounce=500)
    window.dom.document.events.drop += DOMEventHandler(on_drop, True, True)
    claude_connect.refresh_paths()


def run():
    core = Core()
    url = server.start(core)
    core._window = webview.create_window("BetterAnki", url, js_api=core, width=1200, height=820, min_size=(720, 540))
    try:
        webview.start(_bind, (core._window,))
    finally:
        server.stop()
        try:
            core.backup(force=False)  # Anki's periodic backup: skipped if the last one is recent
        finally:
            core._close()
