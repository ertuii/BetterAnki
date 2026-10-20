"""One-click registration of the BetterAnki MCP server in Claude Desktop and Claude Code."""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

NAME = "betteranki"


def server_command() -> dict:
    """Absolute paths only: Claude Desktop starts servers without the user's shell PATH."""
    if getattr(sys, "frozen", False):
        return {"command": sys.executable, "args": ["--mcp"]}
    return {"command": sys.executable, "args": ["-m", "betteranki", "--mcp"]}  # the project's venv python


# ---------- Claude Desktop: edit its JSON config ----------

def _desktop_config() -> Path:
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / "Claude" / "claude_desktop_config.json"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    return Path.home() / ".config" / "Claude" / "claude_desktop_config.json"


def _read_desktop() -> dict:
    f = _desktop_config()
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() and f.read_text(encoding="utf-8").strip() else {}


def _connect_desktop() -> str:
    f = _desktop_config()
    if not f.parent.exists():
        raise RuntimeError("Claude Desktop ist auf diesem Rechner nicht installiert.")
    cfg = _read_desktop()  # raises on broken JSON instead of overwriting the user's other settings
    if f.exists():
        shutil.copy2(f, f.with_name(f.name + ".bak"))
    cfg.setdefault("mcpServers", {})[NAME] = server_command()
    f.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return "Mit Claude Desktop verbunden. Starte Claude Desktop neu, damit es BetterAnki findet."


def _disconnect_desktop():
    cfg = _read_desktop()
    if cfg.get("mcpServers", {}).pop(NAME, None) is not None:
        _desktop_config().write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------- Claude Code: use its CLI ----------

def _claude_cli() -> str | None:
    """The app may run without the login shell's PATH, so also look in the usual install locations."""
    candidates = [shutil.which("claude"), Path.home() / ".local/bin/claude", Path.home() / ".claude/local/claude",
                  Path("/opt/homebrew/bin/claude"), Path("/usr/local/bin/claude")]
    if sys.platform == "win32":
        candidates += [shutil.which("claude.cmd"), Path(os.environ.get("APPDATA", "")) / "npm" / "claude.cmd",
                       Path.home() / ".local/bin/claude.exe"]
    return next((str(c) for c in candidates if c and Path(c).exists()), None)


def _code_entry() -> dict | None:
    f = Path.home() / ".claude.json"
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("mcpServers", {}).get(NAME)
    except (OSError, ValueError):
        return None


def _run(cli: str, *args: str):
    r = subprocess.run([cli, *args], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout).strip() or f"claude {' '.join(args)} fehlgeschlagen")


def _connect_code() -> str:
    cli = _claude_cli()
    if not cli:
        raise RuntimeError("Claude Code wurde nicht gefunden. Installation: https://claude.com/claude-code")
    if _code_entry():
        _run(cli, "mcp", "remove", "-s", "user", NAME)
    _run(cli, "mcp", "add-json", "-s", "user", NAME, json.dumps({"type": "stdio", **server_command()}))
    return "Mit Claude Code verbunden. In neuen Claude-Code-Sitzungen ist BetterAnki verfügbar."


def _disconnect_code():
    cli = _claude_cli()
    if cli and _code_entry():
        _run(cli, "mcp", "remove", "-s", "user", NAME)


# ---------- public ----------

def _state(entry: dict | None) -> str:
    if not entry:
        return "off"
    want = server_command()
    return "on" if entry.get("command") == want["command"] and entry.get("args") == want["args"] else "outdated"


def status() -> dict:
    try:
        desktop_entry = _read_desktop().get("mcpServers", {}).get(NAME)
    except ValueError:
        desktop_entry = None
    return {
        "desktop": {"installed": _desktop_config().parent.exists(), "state": _state(desktop_entry)},
        "code": {"installed": _claude_cli() is not None, "state": _state(_code_entry())},
        # a frozen app outside /Applications is probably still in Downloads/dist and will move
        "unstable_location": getattr(sys, "frozen", False) and sys.platform == "darwin" and not sys.executable.startswith("/Applications/"),
        "command": " ".join([f'"{server_command()["command"]}"', *server_command()["args"]]),
    }


def connect(target: str) -> str:
    return {"desktop": _connect_desktop, "code": _connect_code}[target]()


def disconnect(target: str) -> None:
    {"desktop": _disconnect_desktop, "code": _disconnect_code}[target]()


def refresh_paths() -> None:
    """On app start: if BetterAnki is registered but the app moved, point the entries at the new location."""
    try:
        # only the installed app may claim the entries; a dev run must not repoint them to the project's venv
        if not getattr(sys, "frozen", False) or status()["unstable_location"]:
            return
        if _state(_read_desktop().get("mcpServers", {}).get(NAME)) == "outdated":
            _connect_desktop()
        if _state(_code_entry()) == "outdated":
            _connect_code()
    except Exception:
        pass  # never block app start on this
