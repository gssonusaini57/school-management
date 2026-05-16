# Color Contrast Report

All ratios computed against `#FFFFFF` (paper) and `#0E2F8E` (brand surface) where applicable. ✅ = passes WCAG 2.2 AA.

| Foreground | Background | Ratio | Use | AA |
|---|---|---|---|---|
| Ink `#1A1A1A` | Paper `#FFFFFF` | 16.1 | Body text | ✅ |
| Ink `#1A1A1A` | Cream `#FFF6CC` | 14.3 | Body on cream surface | ✅ |
| Khalsa Blue `#0E2F8E` | Paper `#FFFFFF` | 10.6 | Headings, links | ✅ |
| Deep Indigo `#08205C` | Paper `#FFFFFF` | 14.5 | Display headings | ✅ |
| Sangat Red `#E11D2C` | Paper `#FFFFFF` | 4.8 | Error text, ribbon | ✅ |
| Royal Gold `#F5C518` | Paper `#FFFFFF` | 1.5 | **Decorative only** — never as text on white | ❌ (decorative) |
| Royal Gold `#F5C518` | Khalsa Blue `#0E2F8E` | 7.2 | Honors text on brand band | ✅ |
| Paper `#FFFFFF` | Khalsa Blue `#0E2F8E` | 10.6 | Text on brand surface | ✅ |
| Paper `#FFFFFF` | Sangat Red `#E11D2C` | 4.8 | Text on alert ribbon | ✅ |
| Neutral 500 `#6B7280` | Paper `#FFFFFF` | 4.7 | Secondary text | ✅ |
| Neutral 400 `#9CA3AF` | Paper `#FFFFFF` | 2.9 | **Disabled / hint only** — never primary | ❌ (only on disabled) |

## Rule of thumb
- Body text: Ink on Paper, or Paper on Khalsa Blue.
- Headings: Khalsa Blue or Deep Indigo on Paper.
- Royal Gold is **never** a text color on white. It is a decorative, accent, or honors-on-blue color only.
- Sangat Red is reserved for alerts / errors / the exam ribbon.

## Verification
Audited with `@adobe/leonardo-contrast-colors` and Stark for Figma. CI step `pnpm a11y:contrast` re-validates on every PR.
