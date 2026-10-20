# BetterAnki

Anki-Klon für macOS und Windows mit ruhigem, modernem UI und MCP-Server für Claude.
Unter der Haube läuft Ankis offizieller Kern (`anki` von PyPI): gleiche Planung (SM-2/FSRS), gleiche Dateiformate (.apkg), gleiche Suchsyntax.

Deine Daten liegen lokal:
- macOS: `~/Library/Application Support/BetterAnki/collection.anki2`
- Windows: `%APPDATA%\BetterAnki\collection.anki2`

## Funktionen

- **Heute:** fällige Karten, Semesterstreifen (Lernverlauf + Prognose), Stapel mit Unterstapeln
- **Lernen:** Tastatur (Leertaste, 1–4), Bearbeiten, Rückgängig, Zurückstellen, Audio, Vorlesen (`{{tts de_DE:Feld}}`)
- **Hinzufügen / Browser:** Rich-Text-Felder, Lückentext, Suche mit Anki-Syntax, Filter nach Stapel und Status, Aussetzen, Markieren, Verschieben
- **Stapel-Optionen:** Voreinstellungen, Tageslimits, Lernschritte, Lästlinge, Zurückstellen, **FSRS** inkl. Optimierung
- **Gefilterte Stapel:** Karten per Suche zum Pauken sammeln
- **Statistik:** Wiederholungen, Prognose, Kartenzahlen, Intervalle, Tageszeit, Erinnerung, Antworttasten
- **Notiztypen:** Felder, Kartenvorlagen und CSS bearbeiten, mit Live-Vorschau
- **Einstellungen:** optionale AnkiWeb-Synchronisierung, automatische Sicherungen + Wiederherstellen, Export der ganzen Sammlung, Claude-Befehl zum Kopieren
- **Import/Export:** `.apkg`, `.colpkg`, CSV

Noch nicht: Bild-Verdeckung (Image Occlusion), Add-ons.

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

Tools: `list_decks`, `create_deck`, `rename_deck`, `list_note_types`, `add_notes`, `search_cards`, `get_note`, `update_note`, `delete_notes`, `suspend_cards`, `card_info`, `collection_stats`, `review_statistics`, `create_filtered_deck`, `import_file`, `export_deck`.

Der passende Befehl für deine Installation steht in der App unter **Einstellungen → Claude verbinden**.

## Tastatur

Heute: `Leertaste` lernen, `A` hinzufügen. Lernen: `Leertaste` aufdecken / Gut, `1–4` bewerten, `E` bearbeiten, `-` zurückstellen, `⌘Z` rückgängig, `Esc` zurück. Editor: `⌘↵` speichern, `⌘⇧C` Lückentext.

## Test

```sh
uv run python tests/test_core.py && uv run python tests/test_phase2.py
cd ui && npm run check
```

Lizenz: AGPL-3.0 (wie Anki).
