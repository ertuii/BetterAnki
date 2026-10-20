# BetterAnki

Anki-Klon für macOS und Windows mit ruhigem, modernem UI und MCP-Server für Claude.
Unter der Haube läuft Ankis offizieller Kern (`anki` von PyPI): gleiche Planung (SM-2/FSRS), gleiche Dateiformate (.apkg), gleiche Suchsyntax.

Deine Daten liegen lokal, standardmäßig hier (änderbar unter *Einstellungen → Speicherort*):
- macOS: `~/Library/Application Support/BetterAnki/`
- Windows: `%APPDATA%\BetterAnki\`

## Funktionen

- **Heute:** fällige Karten, Semesterstreifen (Lernverlauf + Prognose; Klick auf einen künftigen Tag lernt dessen Karten vor), Stapel mit Unterstapeln
- **Lernen:** Tastatur (Leertaste, 1–4), Bearbeiten, Rückgängig, Zurückstellen, Audio, Vorlesen (`{{tts de_DE:Feld}}`)
- **Hinzufügen / Browser:** Rich-Text-Felder, Lückentext, Suche mit Anki-Syntax, Filter nach Stapel und Status, Aussetzen, Markieren, Verschieben
- **Stapel-Optionen:** alle Optionen von Anki – Voreinstellungen, Tageslimits (auch nur für diesen Stapel / nur heute), Lernschritte, Lästlinge, Anzeigereihenfolge, Zurückstellen, Audio, Timer, Automatisch weiter, Leichte Tage, SM-2-Faktoren, **FSRS** inkl. Optimierung
- **Gefilterte Stapel:** Karten per Suche zum Pauken sammeln
- **Statistik:** Wiederholungen, Prognose, Kartenzahlen, Intervalle, Tageszeit, Erinnerung, Antworttasten
- **Notiztypen:** Felder, Kartenvorlagen und CSS bearbeiten, mit Live-Vorschau
- **Von Anki umziehen:** erkennt Anki-Profile auf dem Rechner und übernimmt sie mit Lernstand und Medien (ersetzen oder hinzufügen); Anki bleibt unverändert
- **Einstellungen:** Ankis globale Einstellungen (Tageswechsel, Vorauslernen, Zeitlimit, Anzeige, Lastverteilung, Editor, Sicherungsintervalle), optionale AnkiWeb-Synchronisierung, automatische Sicherungen + Wiederherstellen, Export der ganzen Sammlung, Claude-Befehl zum Kopieren
- **Import/Export:** `.apkg`, `.colpkg`, CSV (mit Vorschau, Stapel- und Spaltenwahl), auch per Drag & Drop ins Fenster

- **Eingang für Claude-Karten:** Karten, die Claude anlegt, warten ausgesetzt im Eingang, bis du sie übernimmst, bearbeitest oder verwirfst (abschaltbar)

**Zusatzfunktionen** (gibt es in Anki nicht, einzeln einschaltbar unter *Einstellungen → Zusatzfunktionen*):

- **Prüfungstermine:** Klausurdatum pro Stapel; die App rechnet aus, wie viele neue Karten pro Tag nötig sind (die letzten Tage bleiben fürs Wiederholen) und markiert die Prüfung im Zeitstrahl
- **Lernplan:** Dauer wählen und über alle Stapel lernen, nahe Prüfungen zuerst
- **Schwachstellen:** Themen und Stapel unter deinem Durchschnitt in der Statistik, mit „Üben“ für die vergessenen Karten

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

## Updates ausrollen

1. Version in `src/betteranki/__init__.py` und `pyproject.toml` erhöhen (z. B. `0.3.0`), committen.
2. `git tag v0.3.0 && git push --tags`
3. GitHub Actions baut Mac und Windows und veröffentlicht ein Release mit `BetterAnki-macOS.zip` und `BetterAnki-Windows.zip`.
4. Installierte Apps sehen beim Start „Version 0.3.0 ist da“, ein Klick lädt, ersetzt und startet die App neu. Karten liegen getrennt und bleiben unberührt.

Das Release muss ohne Anmeldung abrufbar sein, das Repo also öffentlich.
Erste Installation bei Freunden (App ist nicht signiert): Mac – App einmal öffnen, dann *Systemeinstellungen → Datenschutz & Sicherheit → Trotzdem öffnen* (nur Apple-Silicon-Macs, der CI-Build ist arm64); Windows – „Weitere Informationen“ → *Trotzdem ausführen*. Updates danach brauchen das nicht mehr.

## Claude anbinden (MCP)

In der App: **Einstellungen → Claude verbinden → Verbinden** (für Claude Desktop und/oder Claude Code). Das war's; Claude Desktop danach einmal neu starten. Verschiebst du die App später, trägt sie den neuen Pfad beim nächsten Start selbst nach.

Läuft die App, schreibt Claude direkt in die offene Sammlung (neue Karten erscheinen sofort im Eingang). Ist sie geschlossen, öffnet der MCP-Server die Sammlung selbst.

Tools: `list_decks`, `create_deck`, `rename_deck`, `list_note_types`, `add_notes`, `search_cards`, `get_note`, `update_note`, `delete_notes`, `suspend_cards`, `card_info`, `collection_stats`, `review_statistics`, `create_filtered_deck`, `import_file`, `export_deck`, `list_inbox`, `difficult_cards`, `weak_spots`, `exam_plan`.

Fertige Abläufe (MCP-Prompts): **Karten aus Material erstellen** (Skript, PDF oder Text → Karten, ohne Dubletten) und **Schwierige Karten verbessern** (oft vergessene Karten analysieren und nach deinem OK umformulieren).

Für andere MCP-Clients steht der Startbefehl unter *Einstellungen → Claude verbinden → Andere MCP-Clients*.

## Tastatur

Heute: `Leertaste` lernen, `A` hinzufügen. Lernen: `Leertaste` aufdecken / Gut, `1–4` bewerten, `E` bearbeiten, `-` zurückstellen, `⌘Z` rückgängig, `Esc` zurück. Editor: `⌘↵` speichern, `⌘⇧C` Lückentext.

## Test

```sh
uv run python tests/test_core.py && uv run python tests/test_phase2.py && uv run python tests/test_phase3.py && uv run python tests/test_phase4.py
cd ui && npm run check
```

Lizenz: AGPL-3.0 (wie Anki).
