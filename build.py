"""Build a standalone app: `uv run python build.py` -> dist/Muisti.app (macOS) or dist/Muisti/Muisti.exe (Windows).

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
    "--name", "Muisti",
    "--windowed",
    "--noconfirm",
    "--paths", str(ROOT / "src"),
    "--add-data", f"{ROOT / 'src/muisti/web'}{sep}muisti/web",
    "--collect-all", "anki",
    "--collect-all", "webview",
    "--osx-bundle-identifier", "app.muisti",
    "--icon", str(ROOT / "assets" / ("icon.ico" if sys.platform == "win32" else "icon.icns")),
])

if sys.platform == "win32":
    # Windows' own unzip marks every file as downloaded ("Mark of the Web"), and .NET then refuses to load
    # pythonnet's and WebView2's DLLs (0x80131515). This config next to the exe lifts that for our own folder.
    (ROOT / "dist" / "Muisti" / "Muisti.exe.config").write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<configuration><runtime><loadFromRemoteSources enabled=\"true\"/></runtime></configuration>\n",
        encoding="utf-8",
    )
