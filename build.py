"""Build a standalone app: `uv run python build.py` -> dist/BetterAnki.app (macOS) or dist/BetterAnki/BetterAnki.exe (Windows).

Builds the UI first. PyInstaller can't cross-compile: run this on each OS (or in CI).
"""

import subprocess
import sys
from pathlib import Path

import PyInstaller.__main__

ROOT = Path(__file__).parent
npm = "npm.cmd" if sys.platform == "win32" else "npm"
subprocess.run([npm, "ci"], cwd=ROOT / "ui", check=True)
subprocess.run([npm, "run", "build"], cwd=ROOT / "ui", check=True)

sep = ";" if sys.platform == "win32" else ":"
PyInstaller.__main__.run([
    str(ROOT / "launcher.py"),
    "--name", "BetterAnki",
    "--windowed",
    "--noconfirm",
    "--paths", str(ROOT / "src"),
    "--add-data", f"{ROOT / 'src/betteranki/web'}{sep}betteranki/web",
    "--collect-all", "anki",
    "--collect-all", "webview",
    "--osx-bundle-identifier", "app.betteranki",
])
