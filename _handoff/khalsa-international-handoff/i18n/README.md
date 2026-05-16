# i18n

Two source files:

| File | Used by |
|---|---|
| `strings.json` | Web (`next-intl`) and mobile (`react-i18next`) UI |
| `document-strings.json` | Print templates (React-PDF) |

## Format

Every leaf is an object with both `en` and `pa` values:

```json
{ "en": "Apply now", "pa": "ਹੁਣੇ ਅਪਲਾਈ ਕਰੋ" }
```

Interpolations use ICU-style `{tokens}`:

```json
{ "en": "Pay ₹{amount}", "pa": "₹{amount} ਭੁਗਤਾਨ ਕਰੋ" }
```

## Wiring

### Web (next-intl)
Place `messages/en.json` and `messages/pa.json` derived from `strings.json` (one file per locale, flattened to dot-keys). The `build:i18n` script in the repo splits the source.

### Mobile (react-i18next)
The mobile app loads `strings.json` directly and indexes into it as `t('mobile.fees.payCta', { amount: '12,500' })`.

## Hard rules

1. **No bare strings in code.** Every visible string must reference an i18n key.
2. **Punjabi is not optional.** A new `en` key without `pa` is a build failure.
3. **Don't translate proper nouns** (school name in English contexts, brand tagline in print, names of people).
4. **Punjabi text in code must use `Noto Sans Gurmukhi`.** Wrap with `<span lang="pa">…</span>` (web) or `{ fontFamily: theme.fontFamily.gurmukhi }` (RN).

## Adding a new locale (e.g. Hindi)

1. Add a third value: `{ "en": "...", "pa": "...", "hi": "..." }`.
2. Add the locale to `next.config.js` (`i18n.locales`) and to the mobile `i18next` init.
3. Add a font fallback in `tokens.css` if the script needs special handling.
4. Validate every key has all three values — the `build:i18n` script will fail loudly otherwise.

## Fallback rule

If a key is missing in `pa`, render the `en` value but log a console warning in dev. **Never** ship a partially-translated build. CI runs `scripts/check-i18n.ts` which fails on missing keys.
