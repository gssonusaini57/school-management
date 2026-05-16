# IconButton

> **Kind:** Atom
> Token-only styling. No raw hex / px / font-family literals.


A square button with a single icon. **Requires `aria-label`.**

## Props

| Prop | Type | Default |
|---|---|---|
| `icon` | `ReactNode` | required |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` |
| `variant` | `'ghost' \| 'subtle' \| 'brand'` | `'ghost'` |
| `aria-label` | `string` | **required** — both languages via i18n |
| `disabled` | `boolean` | `false` |

## Sizes

| Size | Box | Icon |
|---|---|---|
| sm | 32×32 | 16 |
| md | 40×40 | 20 |
| lg | 48×48 | 24 |

## Hard rule

If you need both icon + text, use `<Button leadingIcon=... />` instead.

