# Button

> **Kind:** Atom
> Token-only styling. No raw hex / px / font-family literals.


## Anatomy

```
┌──────────────────────────────────────┐
│  [icon]   Label text   [icon]        │
└──────────────────────────────────────┘
```

## Props

| Prop | Type | Default | Notes |
|---|---|---|---|
| `variant` | `'primary' \| 'secondary' \| 'ghost' \| 'danger'` | `'primary'` | |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` | sm = 32px, md = 40px, lg = 48px |
| `leadingIcon` | `ReactNode` | — | 16px icon, inherits color |
| `trailingIcon` | `ReactNode` | — | |
| `fullWidth` | `boolean` | `false` | |
| `isLoading` | `boolean` | `false` | Replaces label with spinner; keeps width |
| `disabled` | `boolean` | `false` | |
| `as` | `'button' \| 'a'` | `'button'` | When `'a'`, requires `href` |
| `children` | `ReactNode` | required | The label |

## Variants (token-only)

| Variant | Background | Text | Border | Hover bg |
|---|---|---|---|---|
| primary | `color.surface.brand` | `color.text.onBrand` | none | `color.deepIndigo` |
| secondary | `color.surface.page` | `color.text.primary` | `color.border.strong` | `color.surface.raised` |
| ghost | transparent | `color.text.primary` | none | `color.surface.raised` |
| danger | `color.semantic.error` | `color.text.onBrand` | none | darken 8% |

## Sizes

| Size | Height | Padding-x | Font | Radius |
|---|---|---|---|---|
| sm | spacing.8 (32px) | spacing.3 | typography.button (smaller via override) | radius.md |
| md | spacing.10 (40px) | spacing.4 | typography.button | radius.md |
| lg | spacing.12 (48px) | spacing.6 | typography.button @ 17px | radius.md |

## States

| State | Behavior |
|---|---|
| default | per variant |
| hover | bg shifts; cursor pointer |
| focus-visible | 2px outline using `color.border.focus`, offset 2px |
| active | scale 0.98; transition `motion.duration.fast / motion.easing.standard` |
| disabled | opacity 0.4; `cursor: not-allowed`; no hover |
| loading | spinner replaces label; aria-busy="true"; ignores clicks |

## Accessibility

- Native `<button type="button">` unless `as="a"`.
- `isLoading` → `aria-busy="true"` and `aria-live="polite"` on the loading spinner sibling.
- Icon-only buttons must use `<IconButton>` instead — they need explicit `aria-label`.
- Keyboard: `Enter` + `Space` activate. `Tab` to focus.

## Bilingual

The label is just children — caller passes the `t()` result. Never hardcode strings.

```tsx
<Button variant="primary">{t('common.applyNow')}</Button>
```

## Surfaces it appears on

Web: every page. Mobile: most screens. Print: never.

