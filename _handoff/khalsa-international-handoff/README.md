# Khalsa International — Design → Developer Handoff

**School:** Khalsa International Senior Secondary School, Jalalabad, District Patiala
**Affiliation:** Punjab School Education Board (PSEB) · Aff. No. 4906
**Established:** 2005
**Package version:** 1.0 · 2026-05-08

---

## What this is

A single self-contained handoff package describing **everything** a developer needs to implement Khalsa International's three product tracks faithfully:

| Track | Deliverable | Default stack |
|---|---|---|
| **A. Website** | `www.khalsainternational.in` — public marketing + admissions | Next.js 14 (App Router) + TypeScript + Tailwind |
| **B. Mobile App** | Parent / Student companion (6 screens) | React Native + Expo |
| **C. Print Templates** | Letterheads, receipts, report card, salary slip, PSEB admit card | React-PDF |

The brand identity is **locked**. This package encodes — it does not redesign.

---

## How to use this package

1. Open `CLAUDE.md` first. It is the master context for Claude Code.
2. Implement in the order `CLAUDE.md` defines: tokens → i18n → atoms → molecules → organisms → page templates → web pages → mobile screens → print templates.
3. Reference the visual brand book (HTML) for pixel-level intent. Tokens, specs and i18n are the **source of truth** when the two diverge.

---

## Folder map

```
README.md                      ← you are here
CLAUDE.md                      ← master context for Claude Code
brand/                         ← logos, usage rules, voice & tone
design-tokens/                 ← tokens.json + tailwind/rn/css consumers
i18n/                          ← strings.json (en + pa)
components/                    ← shared component library specs
web/                           ← Track A — website
mobile/                        ← Track B — mobile app
documents/                     ← Track C — print templates (schemas + React-PDF)
assets/                        ← icons, illustrations, photo prompts
interactions/                  ← motion + state spec
accessibility/                 ← WCAG checklist + contrast report
responsive/                    ← breakpoints reference
```

---

## Locked-in brand decisions (do not redesign)

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
- **Gurmukhi** — Noto Sans Gurmukhi (Punjabi text on every surface; line-height 1.5)

### Identity
- **Crest mark** — redrawn vector: Khanda + Gurmukhi inscription + gold ring + red ribbon
- **Tagline (English)** — VIDYA · VICHAR · SEVA
- **Tagline (Gurmukhi)** — ਵਿਦਿਆ ਵੀਚਾਰੀ ਤਾਂ ਪਰਉਪਕਾਰੀ
- **Founded** — EST. 2005

### Voice
- Bilingual by default. Punjabi script is **first-class**, not a translation afterthought.
- Tone: rooted, plain-spoken, proud-but-not-boastful — like the principal's letter in the brand book.

---

## Designer Decisions (defaults documented for ambiguous cases)

| Decision | Default chosen | Rationale |
|---|---|---|
| **Mobile track stack** | React Native + Expo (over PWA) | Push notifications and offline-first fee receipts are first-class on RN; Expo keeps it accessible to a small team. |
| **Currency formatting** | `₹ X,XX,XXX.XX` — Indian numbering grouping | Audience is Punjab parents and accountants. Western grouping (`100,000`) reads wrong locally. |
| **Default date format** | `DD MMM YYYY` (e.g. `08 May 2026`) | Matches school office convention. |
| **PSEB document dates** | `DD-MM-YYYY` | PSEB official format — non-negotiable on admit cards / date sheets. |
| **API base URL** | `https://api.khalsainternational.in` | Subdomain placeholder; document for ops to provision. |
| **Career page content** | Reasoned default with one mock vacancy | Page must exist (footer link); content is editable in CMS. |
| **Photography** | Placeholder slots with `PHOTO-PROMPTS.md` | Real photography to be commissioned post-handoff. |

---

## Self-audit

- [x] `CLAUDE.md` references every artifact in this package.
- [x] All component specs reference only tokens that exist in `tokens.json`.
- [x] All page specs use only components that have specs in `components/specs/`.
- [x] All i18n keys used in specs are defined in `i18n/strings.json`; all strings rendered on screens reference an i18n key.
- [x] All sample document data validates against its JSON schema.
- [x] Tokens declared in `tokens.json` are mirrored 1:1 in `tokens.css`, `tailwind.preset.js`, and `rn-theme.ts`.
- [x] Bilingual coverage — every user-facing English string has a Gurmukhi pair.
- [x] No raw hex / px / font-family literals appear in any component or page spec — only token references.

---

## Contact / authorship

- **Design + handoff package** — Claude (Anthropic) on behalf of the school
- **Brand owner** — Khalsa International Sr. Sec. School, Jalalabad
- **Handoff target** — Implementation team via Claude Code

When in doubt, ask the Principal's office (mob. 93563-31762) or e-mail `info@khalsainternational.in`.
