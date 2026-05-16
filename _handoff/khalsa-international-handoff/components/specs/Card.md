# Card

> **Kind:** Molecule
> Token-only styling. No raw hex / px / font-family literals.


## Anatomy
```
┌────────────────────────────────────┐
│ [optional kicker]                  │
│ Heading                            │
│ Body text                          │
│ ─────────                          │
│ [Footer / actions]                 │
└────────────────────────────────────┘
```

Surface: `color.surface.page`. Border: `1px color.border.subtle`. Radius: `radius.lg`. Padding: `spacing.6`. Shadow: none default; `shadow.2` when `elevated`.

Composition: `Card.Header`, `Card.Body`, `Card.Footer` sub-components for predictable layout.

Variants: `default`, `elevated`, `outlined`, `brandSoft` (background `color.surface.brandSoft`).

