---
name: kis-design-system
description: KIS (Khalsa International) brand identity, design tokens, bilingual i18n contract, and component conventions. Read whenever touching the React portal (frontend/), the static public site (public-site/), or PDF templates (backend/app/pdf/). Source of truth lives at packages/design-system/ + _handoff/khalsa-international-handoff/.
---

# Khalsa International — Design System Skill

Read this whenever you touch UI, copy, or print output for KIS. Hard rules first; reference paths at the bottom.

## Brand essentials (locked — do not redesign)

### Colors
| Token | Hex | Role |
|---|---|---|
| Khalsa Blue | `#0E2F8E` | Primary |
| Royal Gold | `#F5C518` | Accent / honors |
| Sangat Red | `#E11D2C` | Alert / ribbon |
| Vasant Cream | `#FFF6CC` | Soft surface |
| Deep Indigo | `#08205C` | Headings / dark surface |
| Ink | `#1A1A1A` | Body text |

### Typography
- **Display** — Playfair Display (long-form headings, hero)
- **Crest caps** — Cinzel (small caps lockups: SENIOR · SECONDARY · SCHOOL)
- **Body / UI** — Manrope (all interface and body copy)
- **Gurmukhi** — Noto Sans Gurmukhi — Punjabi text on every surface, line-height 1.5, **never** falls back

### Identity
- Tagline (English): `VIDYA · VICHAR · SEVA`
- Tagline (Gurmukhi): `ਵਿਦਿਆ ਵੀਚਾਰੀ ਤਾਂ ਪਰਉਪਕਾਰੀ`
- Established: `EST. 2005`
- Affiliation: PSEB Aff. No. 4906

## Hard rules

1. **Never hardcode a color, spacing, or font value.** Reference a token (Tailwind utility from the KIS preset, or a CSS custom property from `tokens.css`).
2. **Every interactive element needs `:focus-visible` styling.** Already wired globally via `tokens.css`; don't strip it.
3. **Punjabi text uses Noto Sans Gurmukhi.** Apply `lang="pa"` to the element (the global selector in `globals.css` flips the font), or use `font-gurmukhi` Tailwind utility.
4. **Every user-facing string is bilingual.** Keys in `packages/design-system/i18n/{en,pa}.json` must always be in lockstep — if you add `en.foo`, you must add `pa.foo`.
5. **Currency** — `₹ 1,00,000.00` (Indian grouping). Use `formatINR()` from `frontend/src/lib/format.ts` (and the Python equivalent in `backend/app/pdf/format.py` once built).
6. **Dates** — default `DD MMM YYYY` (e.g. `08 May 2026`). PSEB documents (admit cards, date sheets) use `DD-MM-YYYY`. Use `formatDate(iso)` and `formatDate(iso, 'pseb')`.
7. **No emoji in product surfaces.** Use icons from `_handoff/.../assets/icons/` or lucide-react.
8. **Every image needs bilingual `alt` text** (or `alt=""` + `role="presentation"` if decorative).
9. **Server timestamps are UTC; UI renders in `Asia/Kolkata`.**

## Surface map (this repo)

| Surface | Stack | Path | Brand tokens come from |
|---|---|---|---|
| Staff/admin portal | React 18 + Vite + Tailwind + shadcn | `frontend/` | `tailwind.config.ts` presets + `globals.css` HSL var remap |
| Public marketing site | Eleventy + Tailwind CLI, **plain HTML output** | `public-site/` | Tailwind preset + `tokens.css` linked into compiled CSS |
| Print PDFs | FastAPI + Jinja2 + WeasyPrint | `backend/app/pdf/` | A mirrored copy of `tokens.css` + bundled `.ttf` fonts in `backend/app/pdf/assets/` |
| Teacher Android app | Kotlin/Compose | `android/` | **Out of scope** — uses Material 3 theme; not retrofitted |
| Teacher iOS app | SwiftUI | `ios/` | **Out of scope** — same |

## How to consume the design system

### React portal (`frontend/`)

```ts
// Tokens are wired automatically:
//   tailwind.config.ts → presets: [require('../packages/design-system/tailwind.preset.cjs')]
//   main.tsx           → import "../../packages/design-system/tokens.css";

// Tailwind utilities (KIS-native):
//   bg-khalsa-blue, text-deep-indigo, bg-vasant-cream
//   font-display, font-body, font-gurmukhi, font-crest
//   text-display, text-heading-xl, text-heading-lg, text-heading-md, text-body, text-caption
//   shadow-1..5, shadow-seal
//   transition-duration-base, ease-standard

// shadcn HSL aliases (still work, mapped onto KIS palette):
//   bg-primary, text-primary-foreground, ring (focus ring), bg-accent, etc.

// Strings:
import { useTranslation } from "react-i18next";
const { t, i18n } = useTranslation();
t("common.applyNow"); // → "Apply now" / "ਹੁਣੇ ਅਪਲਾਈ ਕਰੋ"

// or the wrapper:
import { T, BilingualHeading, BilingualBody } from "@/components/T";
<T k="common.applyNow" />;
<BilingualHeading k="web.home.heroTitle" as="h1" />;
```

### Static public site (`public-site/`)

```html
<!-- Eleventy templates pull tokens.css + Tailwind-compiled utilities -->
<link rel="stylesheet" href="/css/site.css">

<!-- Per-page lang attribute on <html> + utility classes -->
<html lang="en">
  <body class="font-body bg-background text-foreground">
    <h1 class="font-display text-heading-xl text-deep-indigo">…</h1>
  </body>
</html>
```

### Backend PDFs (`backend/app/pdf/` — Sprint 5, not built yet)

```python
# Templates live at backend/app/pdf/templates/*.html.j2
# WeasyPrint reads bundled fonts from backend/app/pdf/assets/fonts/
# tokens.css is mirrored at backend/app/pdf/assets/tokens.css and @import-ed
```

## Component & page index (handoff specs)

- 41 component specs — `_handoff/khalsa-international-handoff/components/specs/<Name>.md`
- 9 web page specs — `_handoff/khalsa-international-handoff/web/pages/<slug>.md`
- 6 mobile screen specs — `_handoff/khalsa-international-handoff/mobile/screens/NN-<slug>.md` (parent app, deferred)
- 6 print template sources (React-PDF, **reference only** — we render via WeasyPrint instead) — `_handoff/khalsa-international-handoff/documents/templates/<Name>.tsx`
- Print sample PDFs — `_handoff/khalsa-international-handoff/documents/samples/<name>-sample.pdf` — what the WeasyPrint output must visually match

## Routing & domain notes

- Staff portal: served at `https://expressonly.in/school/`. `<BrowserRouter basename={import.meta.env.BASE_URL}>` reads from Vite `base: "/school/"`. Don't hardcode `/login` — derive from `BASE_URL`.
- Public site: deploy target TBD. Final target is `khalsainternational.in`; interim could mount under `expressonly.in/` or a subpath. Locale prefix: `/en/...` and `/pa/...` (separate static files per locale, with `hreflang` pairing).
- Print endpoint: `POST /api/pdf/{kind}` (Sprint 5).

## When updating the handoff

If the handoff zip ever updates, regenerate via the `node -e` script in `packages/design-system/README.md`. Do not hand-edit the en/pa JSON drift across the two — they must stay in lockstep on every key.
