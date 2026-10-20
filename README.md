# BetterAnki

Anki-Klon für macOS und Windows mit ruhigem, modernem UI und MCP-Server für Claude.
Unter der Haube läuft Ankis offizieller Kern (`anki` von PyPI): gleiche Planung (SM-2/FSRS), gleiche Dateiformate (.apkg), gleiche Suchsyntax.

Deine Daten liegen lokal:
- macOS: `~/Library/Application Support/BetterAnki/collection.anki2`
- Windows: `%APPDATA%\BetterAnki\collection.anki2`

## Starten (Entwicklung)

```sh
brew install uv            # einmalig (Windows: winget install astral-sh.uv)
cd ui && npm install && npm run build && cd ..
uv run betteranki
```

## App bauen

```sh
uv run python build.py     # -> dist/BetterAnki.app (Mac) bzw. dist/BetterAnki/BetterAnki.exe (Windows)
```
PyInstaller baut nur für das System, auf dem es läuft. Die Windows-Version entsteht auf einem Windows-PC oder über GitHub Actions (`.github/workflows/build.yml`).

## Claude anbinden (MCP)

Claude Code:
```sh
claude mcp add betteranki -- "/Applications/BetterAnki.app/Contents/MacOS/BetterAnki" --mcp
```
Claude Desktop (`claude_desktop_config.json`):
```json
{ "mcpServers": { "betteranki": { "command": "/Applications/BetterAnki.app/Contents/MacOS/BetterAnki", "args": ["--mcp"] } } }
```
Windows: Pfad zur `BetterAnki.exe` statt der Mac-App. Während der Entwicklung geht auch `uv run --directory <projektordner> betteranki --mcp`.

Läuft die App, schreibt Claude direkt in die offene Sammlung (neue Karten erscheinen sofort). Ist sie geschlossen, öffnet der MCP-Server die Sammlung selbst.

Tools: `list_decks`, `create_deck`, `rename_deck`, `list_note_types`, `add_notes`, `search_cards`, `get_note`, `update_note`, `delete_notes`, `suspend_cards`, `card_info`, `collection_stats`, `import_file`, `export_deck`.

## Tastatur

Heute: `Leertaste` lernen, `A` hinzufügen. Lernen: `Leertaste` aufdecken / Gut, `1–4` bewerten, `E` bearbeiten, `-` zurückstellen, `⌘Z` rückgängig, `Esc` zurück. Editor: `⌘↵` speichern, `⌘⇧C` Lückentext.

## Test

```sh
uv run python tests/test_core.py
```

Lizenz: AGPL-3.0 (wie Anki).
