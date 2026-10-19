---
name: feedback_usage_pacing
description: The owner works within Claude's 5-hour usage windows and asked to pace work across a window — cap concurrent agents at 2, keep agents' reading narrow, report status and usage in %, and pause big work near the limit instead of letting agents die mid-run.
metadata:
  type: feedback
---

On 2026-10-19 a 63-agent cross-check workflow (up to 16 verifiers at once, each re-reading the whole change set) burned ~35 % of a 5-hour window in ~20 minutes; the owner said "divide task … so that not filled in 10 minute" and later corrected an over-estimate ("76 % not 80").

**Why:** the owner plans their day around the window; running out mid-task kills agents half-way (it happened twice: an internet drop and a usage limit) and stalls work until the reset.

**How to apply:**
- At most 2 agents at once; fixers/implementers get "read only the files your task names" in the prompt; skip redundant verification waves when early results show near-100 % confirmation.
- Give status as a % table with ETA when asked "status?"; estimate usage from local transcripts and recalibrate when the owner reports the real number.
- If a big step won't fit the remaining window, say so and start it after the reset.
- Workflow resume re-runs every agent call after the first edited one (including finished parallel siblings) — order scripts so the likely-to-change step is last.
