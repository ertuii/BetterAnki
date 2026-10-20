import webview

from . import server
from .core import Core


def run():
    core = Core()
    url = server.start(core)
    core._window = webview.create_window("BetterAnki", url, js_api=core, width=1200, height=820, min_size=(720, 540))
    try:
        webview.start()
    finally:
        server.stop()
        core._close()
