"""In-app updates from GitHub Releases: check, download, swap the app after it quits, restart.

A release (see .github/workflows/build.yml) carries BetterAnki-macOS.zip, BetterAnki-Windows.zip and latest.json.
"""

import json
import os
import ssl
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path

import certifi

from . import __version__

REPO = "ertuii/BetterAnki"
ASSET = "BetterAnki-Windows.zip" if sys.platform == "win32" else "BetterAnki-macOS.zip"


def _parse(v: str) -> tuple:
    try:
        return tuple(int(x) for x in v.strip().lstrip("v").split("."))
    except ValueError:
        return ()


def _get(url: str):
    # the frozen app can't find the system's root certificates, so bring certifi's
    ctx = ssl.create_default_context(cafile=certifi.where())
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "BetterAnki"}), timeout=15, context=ctx)


def app_dir() -> Path:
    """What gets replaced: BetterAnki.app on macOS, the BetterAnki folder next to BetterAnki.exe on Windows."""
    exe = Path(sys.executable)
    return exe.parent if sys.platform == "win32" else exe.parents[2]


def check(manual: bool = False) -> dict | None:
    """The newer release, or None if up to date or running from source. Offline: None, or an error if manual."""
    url = os.environ.get("BETTERANKI_UPDATE_URL")  # for testing against a local fake release
    if not url and not getattr(sys, "frozen", False):
        return None
    try:
        # a release asset, not the GitHub API: the API allows only 60 anonymous requests per hour and IP
        with _get(url or f"https://github.com/{REPO}/releases/latest/download/latest.json") as r:
            rel = json.load(r)
    except (OSError, ValueError) as e:
        if manual:
            raise RuntimeError(f"Update-Suche fehlgeschlagen: {e}") from e
        return None
    if ASSET not in rel.get("assets", {}) or _parse(rel.get("version", "")) <= _parse(__version__):
        return None
    return {"version": rel["version"], "url": rel["assets"][ASSET]}


def install(update: dict) -> None:
    """Download and unpack next to the app, then start a helper that swaps it in once this process exits."""
    target = app_dir()
    if not os.access(target.parent, os.W_OK):
        raise RuntimeError(f"Keine Schreibrechte für {target.parent}. Lade die neue Version bitte manuell herunter.")
    staging = target.parent / ".BetterAnki-update"  # same volume, so the swap is a rename
    _rmtree(staging)
    staging.mkdir()
    zip_path = staging / ASSET
    with _get(update["url"]) as r, open(zip_path, "wb") as f:
        while chunk := r.read(1 << 20):
            f.write(chunk)
    if sys.platform == "darwin":  # ditto keeps the bundle's symlinks and permissions, zipfile does not
        subprocess.run(["ditto", "-x", "-k", str(zip_path), str(staging)], check=True)
    else:
        import zipfile

        zipfile.ZipFile(zip_path).extractall(staging)
    zip_path.unlink()
    new = next(staging.iterdir(), None)
    if new is None or new.name != target.name:
        raise RuntimeError("Das Update-Paket ist unvollständig.")
    _start_swap(target, new, staging)


def _rmtree(p: Path):
    import shutil

    shutil.rmtree(p, ignore_errors=True)


def _start_swap(target: Path, new: Path, staging: Path):
    pid = os.getpid()
    old = target.with_name(target.name + ".old")
    script = Path(tempfile.mkdtemp()) / ("swap.ps1" if sys.platform == "win32" else "swap.sh")
    if sys.platform == "win32":
        target, new, old, staging = (str(p).replace("'", "''") for p in (target, new, old, staging))  # PowerShell quoting
        # ponytail: also stops BetterAnki processes started by Claude (--mcp), Windows can't replace files in use;
        # Claude reconnects on its next start
        script.write_text(f"""
Wait-Process -Id {pid} -ErrorAction SilentlyContinue
Get-Process BetterAnki -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -like '{target}\\*' }} | Stop-Process -Force
Start-Sleep -Milliseconds 500
Remove-Item -LiteralPath '{old}' -Recurse -Force -ErrorAction SilentlyContinue
try {{
  Move-Item -LiteralPath '{target}' -Destination '{old}' -ErrorAction Stop
  Move-Item -LiteralPath '{new}' -Destination '{target}' -ErrorAction Stop
  Remove-Item -LiteralPath '{old}' -Recurse -Force -ErrorAction SilentlyContinue
}} catch {{
  if (-not (Test-Path -LiteralPath '{target}')) {{ Move-Item -LiteralPath '{old}' -Destination '{target}' }}
}}
Remove-Item -LiteralPath '{staging}' -Recurse -Force -ErrorAction SilentlyContinue
Start-Process -FilePath '{target}\\BetterAnki.exe'
""", encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
        subprocess.Popen(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)], creationflags=flags)
    else:
        script.write_text(f"""
while kill -0 {pid} 2>/dev/null; do sleep 0.3; done
rm -rf "{old}"
if mv "{target}" "{old}"; then
  if mv "{new}" "{target}"; then rm -rf "{old}"; else mv "{old}" "{target}"; fi
fi
rm -rf "{staging}"
open "{target}"
""")
        subprocess.Popen(["/bin/sh", str(script)], start_new_session=True,
                         stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
