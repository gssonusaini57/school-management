---
name: sample-report-cards
description: Render sample report-card PNGs (Term 1 per-exam, Term 1 summary, Annual) from a made-up 8th class with the real backend code and local WeasyPrint, for design reviews with the principal — no real student data. Use when the owner asks for a "sample report card" or after changing report-card.html.j2.
---

# Sample report cards

## When to Use
- The owner/principal wants to see the report-card design before approving it.
- After editing `backend/app/pdf/templates/report-card.html.j2` or the payload builder, to eyeball the result (also bump `REPORT_CARD_TEMPLATE_REVISION` — Gotcha #20).

## Inputs / Modes
- Default: three cards for a fictional 8th class (24 students, seeded KIS exam pattern, submitted marks for both terms, grading-subject letters, Apr–Sep attendance with June off and two holidays, English + Punjabi remark, grey photo placeholder).
- Edit `scripts/make_sample.py` (`render(...)` calls at the bottom) for other scopes/layouts.

## Steps
1. Snapshot the code so concurrent edits can't half-break the run:
   `S=<scratch>/rc_sample; mkdir -p $S/snap $S/out; cp -R backend/app $S/snap/app; cp backend/tests/factories.py $S/snap/factories.py`
2. Render (WeasyPrint needs Homebrew's Pango on macOS):
   `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib backend/.venv/bin/python .claude/skills/sample-report-cards/scripts/make_sample.py $S/snap $S/out`
   It prints each card's summary (total, %, grade, rank, attendance, promotion).
3. Convert: `cd $S/out && for f in *.pdf; do pdftoppm -r 130 -png -singlefile "$f" "${f%.pdf}"; done` (poppler from Homebrew).
4. Check: `pdfimages -list sample-term1-each-exam.pdf` must list the photo (288×360); view the PNGs before sending them to the owner.

## Gotchas / FP patterns
- WeasyPrint ignores flex `gap` and collapses `width/height:100%` images in flex boxes (Gotcha #24) — if the photo box is empty or elements touch, that's the cause.
- Fontconfig "ambiguous constant" warnings are noise; filter them.
- The fictional data must stay fictional (names list in the script) — never render real students for a design review.

## Expected Output
`sample-term1-each-exam.png`, `sample-term1-summary.png`, `sample-annual-each-term.png` (A4 at 130 dpi, ~300 KB each) in `$S/out`, ready to send to the owner.
