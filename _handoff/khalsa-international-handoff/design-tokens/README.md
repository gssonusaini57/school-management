# Design Tokens

Source of truth: `tokens.json` (W3C Design Tokens format).

The other three files are generated mirrors — keep them in sync if you edit `tokens.json` (use `style-dictionary` or the small build script suggested in `build.md`).

## Consumers

| File | Used by | How to consume |
|---|---|---|
| `tokens.json` | Style Dictionary, design tools (Figma Tokens plugin) | Import as a build source. |
| `tokens.css` | Web app, Storybook, any HTML target | `@import "design-tokens/tokens.css";` then use `var(--color-khalsa-blue)` etc. |
| `tailwind.preset.js` | Web app | `module.exports = { presets: [require('./design-tokens/tailwind.preset.js')], … }` |
| `rn-theme.ts` | Mobile app | `import theme from './design-tokens/rn-theme';` Wrap app in a ThemeProvider. |

## Rules of use

1. **Reference, don't copy.** Use `var(--space-4)`, not `16px`. Use `theme.surface.brand`, not `'#0E2F8E'`.
2. **No new tokens without the brand owner.** If you need something the system can't express (e.g. a new color), raise it. Don't fork.
3. **Punjabi lines need taller line-height.** `typography.body.pa` and `typography.heading.pa` are not optional — every Gurmukhi block uses them.
4. **Currency, dates, and numbers are not tokens.** They are utilities — see `web/lib/format.ts` and `mobile/lib/format.ts` (see `CLAUDE.md` for spec).
