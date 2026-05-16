---
name: WeasyPrint footer/header pinning uses position fixed
description: For PDF templates rendered via WeasyPrint, pin headers/footers/sig blocks with position fixed (not absolute). Absolute collapses on short content; fixed is rendered on every page at fixed coords.
type: feedback
originSessionId: 065ecbcc-fa71-4b04-95e0-ab8009b0e8a6
---
**Rule:** In any WeasyPrint Jinja template, pin a header / footer / signature block to the page with `position: fixed; top|bottom: 0; left: 0; right: 0;` — never `position: absolute`.

**Why:** `position: absolute; bottom: 0` resolves against the nearest `position: relative` ancestor. When body content is shorter than the page (e.g. a 3-line letter), that ancestor's height collapses to its content and the footer floats up to wherever content ends, not to the A4 bottom. WeasyPrint specifically supports `position: fixed` as "render on every printed page at these coordinates" — exactly what print CSS needs. Verified: footer y_from_bottom went from 200–300pt (broken) to 7–8pt (its own padding) with the switch.

**How to apply:**
- In `backend/app/pdf/templates/_base.html.j2` (or any new shared frame), `.brand-footer` uses `position: fixed; bottom: 0`.
- Add `padding-bottom` on the `.page` wrapper equal to footer height (~42px) so body content can't slide underneath.
- Same trick for the PSEB admit card's signatures block (`pseb-admit-card.html.j2`).
- If you ever add a header that should repeat on every page of a multi-page doc, same pattern with `position: fixed; top: 0`.
