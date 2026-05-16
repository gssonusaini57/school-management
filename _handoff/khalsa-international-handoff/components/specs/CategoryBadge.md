# CategoryBadge

> **Kind:** Molecule
> Token-only styling. No raw hex / px / font-family literals.


Color-coded notice/event category badge. Categories and tokens:

| Category | Bg | Text |
|---|---|---|
| Event | `color.surface.brandSoft` | `color.text.onAccent` |
| Result | `color.semantic.success` (12% tint) | `color.semantic.success` |
| Admission | `color.khalsaBlue` (12% tint) | `color.khalsaBlue` |
| Sports | `color.semantic.warning` (12% tint) | `color.semantic.warning` |
| Exam | `color.sangatRed` (12% tint) | `color.sangatRed` |
| Fees | `color.neutral.200` | `color.text.primary` |

12% tint = `color-mix(in oklch, <token> 12%, white)`.

