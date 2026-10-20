---
version: 1
slug: "ui-src-app-svelte"
primary_target: "ui/src/App.svelte"
related_targets: []
---

Scope: the whole BetterAnki app shell (Heute/Decks, Lernen, Hinzufügen/Editor, Browser). Mode: Operate.
Audience: the owner, a university student reviewing daily on a laptop, day and evening; theme follows OS.
Task: see what is due today, study it by keyboard, add/edit cards, find cards. Claude adds cards via MCP; they appear here.

## Direction contract
THESIS: Every study day is a cell on a semester wall planner; today's due load is the marker block in today's cell. Refuses the card-tile dashboard and the grey-with-one-blue category default.
OWN-WORLD: Paper ground (#fbfaf7 light / graphite #17181b dark), ink text, planner hairlines (#d9d6cf). Marker set is data-only: each deck owns one fixed marker hue (red, blue, green, ochre, violet, teal, pink) across rail chip, strip and browser; counts use Anki semantics blue new / red learning / green review. Archivo, heavy tabular numerals, sentence case, 8px radius controls, no shadows except the study card.
STORY: Launch shows the number due and the semester behind it; one key starts studying; the shell steps back so only the card remains; afterwards the strip's today cell fills in.
FIRST VIEWPORT: Left 248px rail (brand, Heute/Hinzufügen/Browser, deck list with hue chip and due count). Main: date, today's due count at ~112px, three small facts (time estimate, streak, 30-day retention), primary "Alle lernen"; below, the semester strip of day cells (past reviews in intensity steps, today outlined, future dashed with forecast); below, the deck table New/Learn/Review with per-row Lernen and overdue warning chip.
FORM: Semesterplaner, position 4 of 7 grounded candidates; seed: seed:a0d116164438153c.
Signature interaction: the semester strip; hovering a cell reads that day's reviews or forecast; finishing a session fills today's cell. Motion grammar: short ease-out (160ms), study shell fade-back, nothing bouncy; reduced-motion removes it.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
