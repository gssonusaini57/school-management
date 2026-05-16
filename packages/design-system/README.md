# @kis/design-system

Shared design assets for the Khalsa International school surfaces in this repo:

- `frontend/` — staff portal + public marketing pages (Vite + React)
- `backend/` — print PDF templates (FastAPI + WeasyPrint, mirrors a copy of `tokens.css` + fonts)

Source of truth is the handoff package at `_handoff/khalsa-international-handoff/`. Files here are **copies**, kept in lock-step with the handoff. If the handoff updates, regenerate via the `node -e` script in the project root README.

## Layout

```
packages/design-system/
├── tokens.css              CSS custom properties (colors, fonts, spacing, radius, shadow, motion, z)
├── tailwind.preset.cjs     Tailwind preset — `presets: [require('../packages/design-system/tailwind.preset.cjs')]`
├── i18n/
│   ├── en.json             English strings
│   └── pa.json             Punjabi (Gurmukhi) strings — same key shape as en.json
└── brand/                  Crest, wordmarks (SVG)
    ├── crest-full.svg
    ├── crest-mark.svg
    ├── wordmark-en.svg
    └── wordmark-pa.svg
```

## Consumption from frontend

### Tailwind

```ts
// frontend/tailwind.config.ts
import preset from "../packages/design-system/tailwind.preset.cjs";
export default {
  presets: [preset],
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  // …
};
```

### CSS tokens

```css
/* frontend/src/styles/globals.css */
@import "../../../packages/design-system/tokens.css";
```

### i18n

```ts
import en from "../../packages/design-system/i18n/en.json";
import pa from "../../packages/design-system/i18n/pa.json";
i18next.init({ resources: { en: { translation: en }, pa: { translation: pa } } });
```

### Brand SVGs

Either copy/symlink into `frontend/public/brand/`, or import directly via Vite's SVG support:

```tsx
import crestUrl from "../../packages/design-system/brand/crest-mark.svg";
```

## Hard rules (apply everywhere these tokens are consumed)

1. No raw hex / px / font-family literals — token-only.
2. Every interactive element needs `:focus-visible` styling (already wired in `tokens.css`).
3. Punjabi text uses `font-family: var(--font-gurmukhi)` (the `gurmukhi` Tailwind family). Never falls back to Manrope/Playfair.
4. Currency `₹ 1,00,000.00` (Indian grouping). Dates `DD MMM YYYY` everywhere except PSEB documents (`DD-MM-YYYY`).
5. Every i18n key must have both `en` and `pa`.

## Updating from handoff

```sh
# refresh tokens + preset + brand SVGs
cp _handoff/khalsa-international-handoff/design-tokens/tokens.css packages/design-system/tokens.css
cp _handoff/khalsa-international-handoff/design-tokens/tailwind.preset.js packages/design-system/tailwind.preset.cjs
cp _handoff/khalsa-international-handoff/brand/logo/{crest-full,crest-mark,wordmark-en,wordmark-pa}.svg packages/design-system/brand/

# regenerate split locale files
node -e "
const fs=require('fs');
const src=JSON.parse(fs.readFileSync('_handoff/khalsa-international-handoff/i18n/strings.json','utf8'));
const walk=n=>n&&typeof n==='object'&&'en' in n&&'pa' in n&&Object.keys(n).length===2?{en:n.en,pa:n.pa}:Object.keys(n).reduce((a,k)=>{const r=walk(n[k]);a.en[k]=r.en;a.pa[k]=r.pa;return a},{en:{},pa:{}});
const{en,pa}=walk(src);
fs.writeFileSync('packages/design-system/i18n/en.json',JSON.stringify(en,null,2)+'\n');
fs.writeFileSync('packages/design-system/i18n/pa.json',JSON.stringify(pa,null,2)+'\n');
"
```

## Adding portal strings

The handoff covers public-website + parent-mobile-app + print docs. Staff-portal copy isn't in the handoff. As Sprint 4 wraps each portal page in `<T k="..." />`, append keys under a top-level `portal` namespace in **both** `en.json` and `pa.json`. The CI check in `frontend/scripts/check-i18n.mjs` will fail if `pa` is missing.
