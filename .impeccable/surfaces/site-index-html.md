---
version: 1
slug: "site-index-html"
primary_target: "site/index.html"
related_targets: []
---

Scope: public download + feature page for BetterAnki on GitHub Pages (site/index.html, static, separate from app code). Mode: Persuade.
Audience: Anki users anywhere (public), students who already review daily; they arrive from GitHub or search, skeptical of clones and of unsigned apps.
Job: understand it is Anki's real engine with a calmer face plus Claude as card author, then download for their OS and get past the first-launch warning.
Proof: real facts only (v0.3.4, macOS Apple Silicon + Windows, AGPL, Anki core/FSRS/.apkg, local data, MCP). UI is redrawn in HTML/CSS, demo content labelled as example. No stats, no testimonials.
Constraints: no build step, no JS framework, self-hosted Archivo, light/dark via OS, deploy only from site/.

## Direction contract
THESIS: The page proves the mechanism: a request to Claude on the left of the stage turns into cards waiting in BetterAnki's Eingang. Refuses the split hero with device screenshot and a row of feature cards.
OWN-WORLD: The app's semester-planner world: paper #fbfaf7 / graphite #17181b, ink text, planner hairlines, Archivo heavy display with tabular numerals, 8px controls, 14px card radius. Marker hues only on data (deck chips, counts, strip cells, answer underlines), never on chrome.
STORY: Visitor sees the offer and the Claude-to-inbox mechanism, scrolls through redrawn app parts (Heute with semester strip and exam marker, study card), learns the three install steps incl. the honest unsigned warning, downloads.
FIRST VIEWPORT: Top hairline nav. Left column: 3-line display headline ~76px, lede, OS-detected primary download + secondary OS, meta line (version, free, AGPL, local). Right: Claude prompt box, dashed connector, Eingang panel with three cards and Übernehmen. Semester strip runs full width beneath as the page's ruler.
FORM: Claude schreibt, du lernst – position 6 of 7 grounded candidates; seed: seed:d02552885dc32ca8.
Signature interaction: cards drop into the Eingang one by one after the prompt "types"; Übernehmen moves a card out and fills today's strip cell. Motion grammar: 160–400ms ease-out, no bounce, reduced-motion shows the end state.
FINISH: unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
