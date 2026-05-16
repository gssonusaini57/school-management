# Interaction States

Every interactive element must implement all states below. Token references in brackets.

## Button (primary)
- **default** — bg `khalsaBlue`, text `text.onBrand`
- **hover** — bg darken 6% (`color-mix(in srgb, khalsaBlue, black 6%)`)
- **focus-visible** — `outline: 2px solid royalGold`, offset 2px
- **active** — bg darken 12%
- **disabled** — bg `neutral.300`, text `neutral.500`, no pointer-events
- **loading** — spinner replaces label, button stays at default size; `aria-busy="true"`

## Input / Textarea / Select
- **default** — border `neutral.300`
- **hover** — border `neutral.400`
- **focus** — border `khalsaBlue`, ring `khalsaBlue/15` 2px
- **error** — border `sangatRed`, helper text `sangatRed`, `aria-invalid="true"`
- **disabled** — bg `neutral.100`, text `neutral.500`

## Card / Tile (clickable)
- **default** — shadow `elevation.1`
- **hover** — shadow `elevation.2`, translateY -2px (only on devices with hover)
- **focus-visible** — ring `royalGold` 2px

## Empty state
Centered icon + bilingual title + 1-line description + optional CTA.

## Loading state
Skeletons match real layout dimensions (no spinners on full screens). Accent: `neutral.200` shimmer.

## Error state
Icon (red), bilingual title, plain-language message, retry button. Never show stack traces.

## Offline state (mobile)
Persistent banner under top bar: `mobile.errors.offline` (`ਤੁਸੀਂ ਆਫ਼ਲਾਈਨ ਹੋ`). Disable mutations.
