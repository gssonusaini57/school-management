# Input

> **Kind:** Atom
> Token-only styling. No raw hex / px / font-family literals.


## Props

| Prop | Type | Default |
|---|---|---|
| `label` | `string` | **required** (visible OR sr-only via `hideLabel`) |
| `hideLabel` | `boolean` | `false` |
| `hint` | `string` | — |
| `error` | `string` | — overrides hint |
| `leadingIcon` | `ReactNode` | — |
| `trailingAddon` | `ReactNode` | — |
| `size` | `'sm' \| 'md' \| 'lg'` | `'md'` |
| `type` | `'text' \| 'email' \| 'tel' \| 'password' \| 'number'` | `'text'` |
| ...all native input props | | |

## Tokens

- Border radius: `radius.md`.
- Border: `color.border.strong` (1px).
- Focus: ring `color.border.focus` 2px, offset 2px.
- Error: border `color.semantic.error`; helper text `color.semantic.error`.
- Disabled: bg `color.surface.sunken`, text `color.text.muted`.

## Heights

`sm` = 32px · `md` = 40px · `lg` = 48px.

## A11y

- `<label htmlFor>` always present (visually hidden when `hideLabel`).
- `aria-invalid` when `error`.
- `aria-describedby` references hint or error id.

