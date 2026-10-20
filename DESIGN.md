---
name: BetterAnki
colors:
  paper: "#fbfaf7"
  paper-2: "#f3f1ec"
  paper-3: "#ebe8e1"
  ink: "#1c1d21"
  ink-2: "#5d5b55"
  ink-3: "#8a877f"
  rule: "#dcd9d1"
  rule-2: "#c6c2b9"
  marker-red: "#d93a28"
  marker-blue: "#2f6fe0"
  marker-green: "#1e9452"
  marker-ochre: "#d39500"
  marker-violet: "#7a4fd6"
  marker-teal: "#0f8f8a"
  marker-pink: "#d6407f"
typography:
  display: { fontFamily: "Archivo Variable", fontSize: "112px", fontWeight: 800, letterSpacing: "-0.04em" }
  h1: { fontFamily: "Archivo Variable", fontSize: "26px", fontWeight: 750, letterSpacing: "-0.02em" }
  body: { fontFamily: "Archivo Variable", fontSize: "15px", fontWeight: 400, lineHeight: 1.45 }
  label: { fontFamily: "Archivo Variable", fontSize: "12px", fontWeight: 500 }
rounded:
  control: "8px"
  card: "14px"
  chip: "3px"
components:
  button-primary: { backgroundColor: "{colors.ink}", textColor: "{colors.paper}", rounded: "{rounded.control}", padding: "9px 14px" }
  button-ghost: { backgroundColor: "transparent", textColor: "{colors.ink}", rounded: "{rounded.control}", padding: "9px 14px" }
---

# Design System: BetterAnki

## Overview
The semester wall planner. The app is ink on paper with planner hairlines; the only colour is data, drawn like marker on a printed planner. Calm, dense, keyboard-first. Light and dark follow the OS (dark = graphite paper `#17181b`, markers brightened).

## Colors
### Primary
Ink `#1c1d21` on paper `#fbfaf7`: all chrome, primary buttons, focus rings.
### Neutral
Paper steps (`paper-2` hover, `paper-3` selected) and hairlines (`rule`, `rule-2`).
### Named Rules
- **Markers are data.** The seven marker hues appear only on data: deck chips, counts, strip cells, flags, answer-button underlines. Never on chrome.
- **One hue per deck, forever.** Top-level deck hue = `deck_id % 7`; subdecks inherit it.
- **Anki semantics for counts:** new = blue, learning = red, review = green; zero counts drop to `ink-3`.

## Typography
Archivo (self-hosted variable). Hierarchy by size contrast only: today's due count at display size, everything else 12–26px. Numbers always tabular.

## Layout
248px rail + work area. Study mode collapses the rail to zero: only the card remains. Pages pad 32×40px.

## Elevation & Depth
Flat. Only two things float: the study card (soft two-layer shadow) and menus/sheets/toasts.

## Shapes
Controls 8px, study card 14px top corners, deck chips 3px squares, warning pills fully round.

## Components
### Semester strip (signature)
One cell per day: past cells in three heat steps of blue by reviews done, today outlined in ink, future cells dashed (solid outline when reviews are forecast). Hover lifts a cell and the title reads the day. Narrow windows drop old days, never shrink cells below ~6px.
### Buttons
Primary ink-filled; ghost hairline; plain text-only for tertiary actions. Shortcut hints as `kbd`.
### Inputs
Hairline `rule-2`, ink border on focus. Card fields are contenteditable rich text.
### Navigation
Rail items: icon + label, `paper-3` fill when active.

## Do's and Don'ts
### Do:
- Show the next decision only on the study screen (Space, then 1–4).
- Render card HTML in a sandboxed iframe with its own CSS.
### Don't:
- Use marker colours for decoration or chrome.
- Add cards-as-layout dashboards, gradients, or badges beyond the overdue pill.
