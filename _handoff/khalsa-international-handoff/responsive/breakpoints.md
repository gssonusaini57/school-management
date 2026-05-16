# Responsive Breakpoints

Mobile-first. Tailwind defaults preserved.

| Token | Min width | Typical device |
|---|---|---|
| `sm` | 640 px | Large phone, small tablet portrait |
| `md` | 768 px | Tablet portrait |
| `lg` | 1024 px | Tablet landscape, small laptop |
| `xl` | 1280 px | Desktop |
| `2xl` | 1536 px | Large desktop |

## Layout shifts

**Site header**
- < md: hamburger menu, logo centered, "Apply" CTA right
- ≥ md: full nav inline

**Hero**
- < md: stacked, image first
- ≥ md: 50/50 split

**Stats strip**
- < sm: 2×2 grid
- ≥ sm: 4-column row + award badge

**Program grid**
- < md: 1 column
- md: 2 columns
- ≥ lg: 3 columns

**Notice board**
- < md: vertical list
- ≥ md: 2-column grid (latest 6)

**Footer**
- < md: stacked sections
- ≥ md: 4-column

## Type scale
Body stays 16 px across all breakpoints. Display heading scales: 36 / 44 / 56 / 72 px at sm / md / lg / xl. Use `clamp()` for hero: `clamp(2.25rem, 4vw + 1rem, 4.5rem)`.

## Touch targets
≥ 44 × 44 px on all touch surfaces. Mobile tab bar buttons 56 px tall.
