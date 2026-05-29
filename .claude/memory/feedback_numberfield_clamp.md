---
name: feedback-numberfield-clamp
description: For bounded numeric inputs (max marks, max-X fields) use NumberField + global spinner removal. Hard-clamps on every keystroke. Raw <Input type="number"> kept the "100 → 31" bug.
metadata:
  type: feedback
---

For any bounded numeric input in the React portal, use [`<NumberField>`](frontend/src/components/ui/number-field.tsx) instead of raw `<Input type="number">`. The base Input already hides the HTML spin-button arrows globally — that part you get for free everywhere.

**Why:** teachers entering Max Marks hit a recurring "100 → 31" data-entry bug — they'd brush the spin-arrow (incrementing the value), type "3" (which appended instead of replacing), then struggle to backspace through `Number(e.target.value) || 100` fallbacks that reset to default whenever the field went briefly empty. Confirmed by user feedback in Session 13 with a screenshot. Fixed app-wide via two changes: spinners hidden in [components/ui/input.tsx](frontend/src/components/ui/input.tsx) (CSS `appearance:textfield + ::-webkit-{inner,outer}-spin-button`), and NumberField stores state as a `string` (empty allowed), enforces `max`/`min` by *rejecting* keystrokes that would push the parsed value out of range — the controlled input snaps back to the last valid value.

**How to apply:**
- Any new bounded number input → `<NumberField value={str} onChange={setStr} max={N} min={0}>`. State stays `string` (allowing `""`), parent coerces with `Number(str) || 0` at submit.
- Unbounded inputs (display order, annual fee with no upper limit) can still use `<Input type="number">` if state is already string-based via `digitsOnly()`.
- Never write `onChange={(e) => setState(Number(e.target.value) || N)}` — that's the bug. Always allow `""`.
- Don't try to re-introduce HTML spinner arrows by overriding `[appearance:textfield]`. They're hidden on purpose.
- Related: [[project-marks-batches-workflow]] (uses NumberField for per-student entry).
