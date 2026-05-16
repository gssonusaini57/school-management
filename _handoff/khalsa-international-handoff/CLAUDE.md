# CLAUDE.md — Master implementation context for Claude Code

> Read this file first. It is the source of truth for how to build everything in this package.

## Project summary

Khalsa International Senior Secondary School (Jalalabad, Patiala — PSEB Aff. 4906, est. 2005) needs three production deliverables: a public marketing **website**, a parent/student **mobile app**, and a set of **print templates** rendered as PDFs. All three share one brand system, one token set, and one bilingual (English + Gurmukhi Punjabi) string library.

## Tech stacks per track

| Track | Stack | Entry command |
|---|---|---|
| Website | Next.js 14 (App Router) + TypeScript + Tailwind CSS + `next-intl` | `pnpm dev` |
| Mobile | React Native + Expo SDK 51 + TypeScript + `expo-router` + `react-i18next` | `pnpm expo start` |
| Documents | `@react-pdf/renderer` + Zod (for schema validation) | `pnpm render:samples` |

## Where to find what

| Need | Path |
|---|---|
| Color / type / spacing tokens | `design-tokens/tokens.json`, `tokens.css`, `tailwind.preset.js`, `rn-theme.ts` |
| Translatable strings | `i18n/strings.json` (UI), `i18n/document-strings.json` (print) |
| Brand assets (logo, favicon, social) | `brand/logo/` |
| Brand usage rules | `brand/usage-rules.md`, `brand/voice-and-tone.md` |
| Shared component specs | `components/specs/<name>.md` |
| Web sitemap | `web/information-architecture.md` |
| Web page specs | `web/pages/<slug>.md` |
| SEO meta per page | `web/seo-checklist.md` |
| Mobile architecture | `mobile/app-architecture.md` |
| Mobile screen specs | `mobile/screens/<NN-name>.md` |
| Document schemas (Zod-compatible JSON Schema) | `documents/schemas/<name>.schema.json` |
| React-PDF templates | `documents/templates/<Name>.tsx` |
| Sample rendered PDFs | `documents/samples/` |
| Motion / interaction states | `interactions/motion-spec.md`, `interactions/states.md` |
| Accessibility checklist | `accessibility/a11y-checklist.md` |
| Breakpoints | `responsive/breakpoints.md` |

## Implementation order

Do not skip ahead. Each step depends on the one above.

1. **Tokens.** Wire up `tokens.css` (web) and `rn-theme.ts` (mobile). Apply the Tailwind preset.
2. **i18n setup.** Install `next-intl` (web) and `react-i18next` (mobile). Load `strings.json`. Set `pa` (Punjabi) as a fully-supported locale, not a fallback.
3. **Atoms.** `Button`, `IconButton`, `Input`, `Textarea`, `Select`, `Checkbox`, `Radio`, `Switch`, `Badge`, `Pill`, `Avatar`, `Tag`. Build in Storybook with all states.
4. **Molecules.** `Card`, `StatTile`, `NoticeCard`, `TimetableSlot`, `SubjectRow`, `FeeRow`, `TestimonialCard`, `ProgramCard`, `HouseTag`, `BilingualHeading`, `BilingualBody`, `CategoryBadge`, `StatusPill`.
5. **Organisms.** `SiteHeader`, `SiteFooter`, `HeroBlock`, `StatsStrip`, `ProgramGrid`, `PrincipalLetter`, `GalleryStrip`, `VoicesGrid`, `NoticeBoard`, `AdmissionsCTA`, `MobileTabBar`, `MobileTopBar`, `WeekStrip`.
6. **Page templates.** Compose organisms into the layouts described in `web/pages/`.
7. **Web pages.** Implement all 9 pages with i18n + SEO meta + responsive behavior verified at every breakpoint.
8. **Mobile screens.** Implement all 6 screens. Wire navigation per `mobile/app-architecture.md`.
9. **Print primitives.** `LetterheadHeader`, `LetterheadHeaderModern`, `LetterheadFooter`, `SealStamp`, `SignatureBlock`, `PdfTable`.
10. **Print templates.** Implement six React-PDF templates. Render samples. Compare byte-for-byte against `documents/samples/`.

## Coding conventions

- **Files** — kebab-case (`fee-row.tsx`).
- **Components** — PascalCase (`FeeRow`).
- **Hooks** — camelCase, prefixed `use` (`useFeeStatus`).
- **Props** — boolean props phrased positively (`isPaid`, not `isUnpaid`).
- **i18n keys** — dot-namespaced by surface (`web.home.heroTitle`, `mobile.fees.payNowCta`, `docs.reportCard.subjectHeading`).
- **Folders (web)** — `app/`, `components/{atoms,molecules,organisms}`, `lib/`, `i18n/`, `styles/`.
- **Folders (mobile)** — `app/`, `components/`, `screens/`, `hooks/`, `services/`, `i18n/`.
- **Folders (documents)** — `templates/`, `schemas/`, `samples/`, `render.ts`.

## Definition of done

### A component is done when…
- It renders correctly across every state in `interactions/states.md` (default / hover / focus-visible / active / disabled / loading / error / empty).
- It accepts only token references — no raw colors, font-families or pixel values.
- It has a Storybook story per variant.
- It passes a11y audit at WCAG 2.2 AA (axe in CI).
- It supports both `en` and `pa` content. Punjabi rendering uses Noto Sans Gurmukhi with line-height 1.5.

### A web page is done when…
- All static copy is keyed through `next-intl`. Switching locale to `pa` swaps every visible string.
- SEO meta (title / description / OG / Twitter / canonical / hreflang `en` ↔ `pa`) matches `web/seo-checklist.md`.
- Lighthouse scores ≥ 90 across Performance / Accessibility / Best-Practices / SEO on a 4G connection.
- Layout verified at `sm`, `md`, `lg`, `xl`, `2xl`.
- All images have bilingual `alt` text (or are decorative with `alt=""` and explicit role).

### A mobile screen is done when…
- It works on iOS 16+ and Android 11+.
- Loading / empty / populated / error / offline states all handled.
- Both languages render correctly, including font fallbacks.
- Navigation in/out matches `mobile/app-architecture.md`.

### A print template is done when…
- It renders to PDF identical to the sample at `documents/samples/` (compare via PDF text + visual diff).
- Input data validates against its schema.
- Currency rendered as `₹ X,XX,XXX.XX`. Indian numbering grouping mandatory.
- Bilingual fields render correctly when supplied.

## Hard rules

1. **Never hardcode a color, spacing or font value.** Always reference a token.
2. **Every interactive element needs `:focus-visible` styling.** No exceptions.
3. **Every image needs `alt` text in both languages** (or is decorative with `alt=""`).
4. **Every form control needs an associated label.** `aria-label` is acceptable when visual labels are intentionally absent.
5. **Punjabi text must use `Noto Sans Gurmukhi`.** Never fall back to Manrope or Playfair.
6. **Currency** — always `₹ X,XX,XXX.XX` with Indian grouping (`1,00,000` not `100,000`). Use the `formatINR` util.
7. **Dates** — default `DD MMM YYYY` (e.g. `08 May 2026`); PSEB documents and admit cards use `DD-MM-YYYY`.
8. **No emoji in product surfaces.** Use icons from `assets/icons/`.
9. **Every async surface has a skeleton or spinner.** No bare `null` returns during loading.
10. **Server timestamps are UTC; UI renders in `Asia/Kolkata`.**
