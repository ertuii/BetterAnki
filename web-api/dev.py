"""Runs the worker locally on 127.0.0.1:4322 (vite preview proxies /api there). PYTHONPATH=src uv run python web-api/dev.py"""
from http.server import ThreadingHTTPServer

from worker import handler

ThreadingHTTPServer(("127.0.0.1", 4322), handler).serve_forever()
