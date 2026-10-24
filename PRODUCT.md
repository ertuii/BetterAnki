# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack
Desktop app (macOS + Windows): Python 3.12 backend on Anki's official `anki` package, native window via pywebview, UI in Svelte 5 + Vite built to static files. Chosen by the assistant for easiest setup; user has no desktop-app experience.

## Users
The owner: a university student who studies exam material daily on a laptop with spaced repetition.

## Product Purpose
A full Anki clone that keeps Anki's scheduling and file compatibility (.apkg, FSRS, cloze, media) but feels calm and modern, and lets Claude create and manage cards through a local MCP server. Success: the daily review habit is pleasant, and turning lecture material into cards takes one request to Claude.

## Positioning
Anki's real engine with an AI author attached: Claude writes cards straight into the local collection, the app is where you review them.

## Operating Context
Daily review sessions on a laptop, both during the day (library/university) and in the evening; theme follows the OS light/dark setting. The collection lives on the laptop; with an optional Muisti account it is also synced row by row to Supabase, for the web app (Vercel) and other computers. Keyboard-driven review (Space to reveal, 1–4 to answer).

## Capabilities and Constraints
- Decks with subdecks, due counts (new / learning / review), study screen, add/edit notes, browser with Anki search syntax, suspend/flag/move, undo, .apkg/CSV import, .apkg export.
- MCP server (stdio) for Claude: list/create decks, add/search/update/delete notes, stats, import/export.
- Later phases: statistics graphs, note type/template editor, deck options and FSRS tuning, filtered decks, optional AnkiWeb sync.
- Card content is user/Claude-authored HTML with its own CSS; rendered isolated from the app chrome.

## Brand Commitments
Name: Muisti. Priorities the user stated: calmer, modern UI without legacy clutter; better overview of progress and what is due.

## Evidence on Hand
No logo, screenshots, or user data yet. Do not invent usage stats or testimonials.

## Product Principles
- The review screen is sacred: nothing competes with the card.
- What is due today is visible immediately on launch.
- Anki compatibility over novelty: never break the user's collection or Anki's mental model.
- Claude is a first-class author, not a gimmick: its cards look and behave like any other.
