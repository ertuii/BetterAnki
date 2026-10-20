"""MCP stdio server. Forwards to the running app (the collection is exclusively locked),
or opens the collection itself for the duration of one call when the app is closed."""

import json
import threading
import urllib.request

from mcp.server import MCPServer

from .core import Core
from .server import INFO_FILE

mcp = MCPServer("BetterAnki")
_open_lock = threading.Lock()  # tool calls run in parallel threads; the collection opens once at a time


def call(method: str, **args):
    try:
        info = json.loads(INFO_FILE.read_text())
        req = urllib.request.Request(
            f"http://127.0.0.1:{info['port']}/rpc",
            data=json.dumps({"method": method, "args": args}).encode(),
            headers={"X-Token": info["token"], "Content-Type": "application/json"},
        )
        body = json.loads(urllib.request.urlopen(req, timeout=60).read())
    except (FileNotFoundError, ConnectionError, urllib.error.URLError):
        with _open_lock:
            core = Core()  # app not running
            try:
                return getattr(core, method)(**args)
            finally:
                core._close()
    if "error" in body:
        raise RuntimeError(body["error"])
    return body["result"]


@mcp.tool()
def list_decks() -> list[dict]:
    """All decks as a tree with new/learn/review counts due today."""
    return call("decks")


@mcp.tool()
def create_deck(name: str) -> int:
    """Create a deck (use '::' for subdecks, e.g. 'Spanisch::Verben'). Returns the deck id."""
    return call("create_deck", name=name)


@mcp.tool()
def rename_deck(deck_id: int, name: str) -> None:
    """Rename a deck."""
    return call("rename_deck", deck_id=deck_id, name=name)


@mcp.tool()
def list_note_types() -> list[dict]:
    """Note types with their field names. Use these names as keys in add_notes."""
    return call("note_types")


@mcp.tool()
def add_notes(notes: list[dict]) -> list:
    """Add notes in bulk. Each note: {"deck": "Deck::Name", "notetype": "Basic", "fields": {"Front": "...", "Back": "..."}, "tags": ["a"]}.
    Fields may contain HTML. For cloze use notetype "Cloze" with {"Text": "{{c1::Berlin}} ist die Hauptstadt"}.
    Returns the new note id, or an error string, per note."""
    results = []
    for n in notes:
        try:
            results.append(call("add_note", notetype=n.get("notetype", "Basic"), deck=n["deck"], fields=n["fields"], tags=n.get("tags", [])))
        except Exception as e:
            results.append(f"error: {e}")
    return results


@mcp.tool()
def search_cards(query: str = "", limit: int = 100) -> list[dict]:
    """Search with Anki syntax: 'deck:Spanisch', 'tag:verb', 'is:due', 'is:new', 'is:suspended', 'prop:ivl>30', 'rated:7', 'front:*haus*', free text. Empty = all."""
    return call("search", query=query, limit=limit)


@mcp.tool()
def get_note(note_id: int) -> dict:
    """Full note: fields, tags, deck, card ids."""
    return call("get_note", note_id=note_id)


@mcp.tool()
def update_note(note_id: int, fields: dict | None = None, tags: list[str] | None = None, deck: str | None = None) -> None:
    """Change some fields, replace the tag list, and/or move the note's cards to another deck."""
    return call("update_note", note_id=note_id, fields=fields, tags=tags, deck=deck)


@mcp.tool()
def delete_notes(note_ids: list[int]) -> int:
    """Delete notes and their cards. Returns number deleted."""
    return call("delete_notes", note_ids=note_ids)


@mcp.tool()
def suspend_cards(card_ids: list[int], suspended: bool = True) -> None:
    """Suspend (or unsuspend) cards."""
    return call("suspend", card_ids=card_ids, suspended=suspended)


@mcp.tool()
def card_info(card_id: int) -> str:
    """Review history and scheduling details of a card (HTML)."""
    return call("card_info", card_id=card_id)


@mcp.tool()
def collection_stats() -> dict:
    """Total cards/notes, cards due today, what was studied today."""
    return call("stats")


@mcp.tool()
def review_statistics(deck_id: int | None = None, days: int = 30) -> dict:
    """Study statistics: today's answers, reviews per day, forecast of due cards, card counts by state,
    interval distribution, answer buttons, true retention. days: 30, 90 or 365."""
    return call("statistics", deck_id=deck_id, days=days)


@mcp.tool()
def create_filtered_deck(name: str, search: str, limit: int = 100) -> int:
    """Gather cards matching an Anki search into a temporary study deck (e.g. 'deck:Statistik is:due' for cramming)."""
    return call("create_filtered_deck", name=name, search=search, limit=limit)


@mcp.tool()
def import_file(path: str) -> str:
    """Import an .apkg or .csv/.txt/.tsv file from an absolute path. (.colpkg replaces the whole collection: only on explicit user request.)"""
    return call("import_file", path=path)


@mcp.tool()
def export_deck(path: str, deck_id: int | None = None) -> int:
    """Export a deck (or everything if no deck_id) as .apkg to an absolute path."""
    return call("export_deck", path=path, deck_id=deck_id)


def run():
    mcp.run()
