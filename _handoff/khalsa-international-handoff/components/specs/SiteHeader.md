# SiteHeader

> **Kind:** Organism
> Token-only styling. No raw hex / px / font-family literals.


## Anatomy
```
┌──────── announcement bar (surface.brand, text.onBrand, height 32px) ────────┐
├──── nav row (surface.page, height 72px) ──────────────────────────────────────┤
│ [crest] Khalsa International / SR. SEC. SCHOOL    Nav · Nav · Nav  [Apply]  │
└──────────────────────────────────────────────────────────────────────────────┘
```

Sticky to top after first scroll; reduces height to 56px and drops the announcement bar.

Mobile: collapses to logo + hamburger; full-screen drawer with the same nav items + bilingual labels stacked.

A11y: `<header role="banner">`, nav `<nav aria-label="Primary">`, drawer trapped focus with `Esc` to close.

