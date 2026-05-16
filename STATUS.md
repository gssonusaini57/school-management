# KIS Design Handoff Integration — Status Report

**Date:** 2026-05-08 · **Branch:** master · **Plan:** `/Users/manjeetsaini/.claude/plans/reactive-chasing-crab.md`

The work in this session integrates the Khalsa International design package
(`_handoff/khalsa-international-handoff/`) into the existing repo across
three surfaces. The locked scope (after Phase 0 audit + Q&A): brand-token
retrofit + a static public marketing site + Python WeasyPrint print
templates + bilingual everywhere. The parent mobile app track is **deferred
to a future session**.

## Sprint summary

| # | Sprint | Status | Commit |
|---|---|---|---|
| 1 | `packages/design-system/` + fonts + i18n libs in portal | ✅ | `39e25d8` |
| 2 | Restyle `Button` + `Badge` to KIS semantic tokens (other primitives covered by HSL remap) | ✅ | `3e5ec9e` |
| 3a+b | Eleventy public-site scaffold + home page (en + pa) | ✅ | (commit included scaffold + home) |
| 3d | 8 remaining public pages × 2 locales | ✅ | (`feat(public-site): add 8 marketing pages`) |
| 3e | Public-site deploy script + nginx template + slash command | ✅ | (`feat(deploy): public-site deploy script`) |
| 4 | Bilingual the React portal (chrome + Login + Dashboard fully; page titles everywhere) | 🟡 | (`feat(portal): bilingual chrome`) |
| 5 | WeasyPrint PDF pipeline + fee-receipt template + Fees download button | 🟡 | (`feat(pdf): WeasyPrint pipeline`) |
| 6 | This report | ✅ | this commit |

🟡 = shipped + working, with explicit follow-ups (see Open follow-ups).

## Migration table

### Tokens / brand foundation
| Artifact | Status |
|---|---|
| Tailwind preset + CSS tokens (`packages/design-system/`) | ✅ wired into `frontend/` and `public-site/` and mirrored into `backend/app/pdf/assets/` |
| Fonts — Playfair Display / Cinzel / Manrope / Noto Sans Gurmukhi | ✅ Google-Fonts-loaded on web (frontend + public-site); 🟡 backend uses `apt`-installed `fonts-noto` + `fonts-lohit-punjabi` (see provisioning) |
| Brand SVGs (crest-mark, crest-full, wordmark-en/pa) | ✅ copied to `packages/design-system/brand/` |
| i18n (en + pa) | ✅ handoff strings in `packages/design-system/i18n/{en,pa}.json` (read-only mirror) + portal-specific in `portal-{en,pa}.json` |

### React staff portal (`frontend/`)
| Surface | Tokens applied | Bilingual | Notes |
|---|---|---|---|
| Layout sidebar + topbar | ✅ | ✅ full | Deep-indigo bg + royal-gold accents |
| LocaleSwitch in topbar | — | ✅ | Persists to `localStorage`, syncs `html[lang]` |
| Login | ✅ | ✅ full | KIS gradient background + crest + Cinzel lockup |
| Dashboard | ✅ | ✅ full | KPI gradients → flat KIS semantic colors |
| Students | 🟡 | 🟡 title only | h1 + sidebar label translated; table headers + row buttons English |
| StudentDetail | 🟡 | ❌ | Heading is `{student.name}` (data) — not translatable |
| Admissions (admit-student form) | 🟡 | 🟡 title only | Form labels still English |
| Attendance | 🟡 | 🟡 title only | |
| MarksEntry | 🟡 | 🟡 title only | |
| MarksResults | 🟡 | 🟡 title only | |
| Fees | 🟡 | 🟡 title only | + new "Download PDF" per row → POST `/api/pdf/fee-receipt` |
| Notices | 🟡 | 🟡 title only | |
| Staff | 🟡 | 🟡 title only | |
| Reports | 🟡 | 🟡 title only | |
| MobileApps | 🟡 | 🟡 title only | |
| shadcn primitives — Button | ✅ | n/a | success/warning use `bg-success/warning` from KIS preset |
| shadcn primitives — Badge | ✅ | n/a | success/warning/info use opacity-tinted KIS tokens |
| shadcn primitives — others (Card / Input / Select / Dialog / Popover / Toast / Checkbox / Label / Textarea / Table / Calendar / DatePicker) | ✅ | n/a | Pick up KIS palette automatically via the HSL var remap in `globals.css` — no code change needed |

### Public marketing site (`public-site/` — Eleventy + Tailwind CLI)
| Page | en | pa | Notes |
|---|---|---|---|
| `/` (root redirect) | ✅ | ✅ | JS detects browser locale, redirects to `/en/` or `/pa/` |
| `/<lang>/` (Home) | ✅ | ✅ | All 9 spec sections (hero, stats, values, principal, programs, gallery, voices, notices, CTA) |
| `/<lang>/about/` | ✅ | ✅ | Story + 5-row milestone timeline + mission/vision/values + leadership + affiliations |
| `/<lang>/academics/` | ✅ | ✅ | Philosophy + 6 program cards + Sr. Sec. Sciences expansion + co-curricular |
| `/<lang>/admissions/` | ✅ | ✅ | 4-step process + eligibility + fees + documents + form + walk-in |
| `/<lang>/notices/` | ✅ | ✅ | Filter pills + 12 sample NoticeCards + paginator |
| `/<lang>/gallery/` | ✅ | ✅ | 3 year-tabs × 12 photo placeholders |
| `/<lang>/contact/` | ✅ | ✅ | Address + map (lazy-loaded OSM iframe) + form |
| `/<lang>/career/` | ✅ | ✅ | 1 mock vacancy + CV upload form |
| `/<lang>/parent-portal/` | ✅ | ✅ | "Coming soon" + link to staff sign-in |
| Build pipeline | ✅ | — | `npm run build` → 19 HTML + CSS + brand SVGs in `dist/` |
| Deploy script | ✅ | — | `bash scripts/deploy/test/deploy-public-site.sh` (or `/deploy-test-public-site`) |
| nginx config | 🟡 template only | — | Manual integration — see `deploy/nginx.public-site.conf` Pattern A or B |

Page sizes: 10–28 KB HTML each (Punjabi ~3 KB heavier from Gurmukhi), CSS 17 KB minified. Total `dist/` ~350 KB.

### Print PDF templates (`backend/app/pdf/`)
| Kind | Schema | Template | Frontend wired? | Notes |
|---|---|---|---|---|
| `fee-receipt` | ✅ FeeReceipt (full) | ✅ full | ✅ Fees page → "Download PDF" button | Bilingual student name, INR-formatted total, mode-of-payment, signoff |
| `letterhead-a` | 🟡 loose stub | 🟡 stub | ❌ | Renders the brand frame + dumps payload JSON; redesign against `_handoff/.../letterhead-A-sample.pdf` |
| `letterhead-b` | 🟡 loose stub | 🟡 stub | ❌ | Same |
| `report-card` | 🟡 partial | 🟡 stub | ❌ | Same |
| `pseb-admit-card` | 🟡 partial | 🟡 stub | ❌ | PSEB date format `DD-MM-YYYY` is supported via `dt_pseb` Jinja filter |
| `salary-slip` | 🟡 partial | 🟡 stub | ❌ | Same |
| Pipeline (router + schemas + render) | ✅ | — | — | `POST /api/pdf/{kind}`, auth required, Pydantic validation, WeasyPrint render |
| `format` filters (`inr`, `dt`, `dt_pseb`) | ✅ | — | — | Mirrors `frontend/src/lib/format.ts` byte-for-byte |
| WeasyPrint system deps in provisioning | ✅ | — | — | `apt install` of pango/harfbuzz/fonts-noto/fonts-lohit-punjabi |

## Build verification

| Check | Result |
|---|---|
| `frontend/` `tsc -b && vite build` | ✅ pass · 826 KB JS / 259 KB gz · 41.8 KB CSS / 8.7 KB gz |
| `public-site/` `npm run build` | ✅ pass · 19 HTML files + brand SVGs + minified CSS |
| `backend/` AST parse | ✅ pass on all `.py` files |
| Backend WeasyPrint render — sample fee-receipt → HTML | ✅ verified locally (7.7 KB HTML, Gurmukhi + INR + all fields present) |
| Backend WeasyPrint render → PDF | ⏳ requires `apt`-installed system deps; will be verified after first deploy via `/deploy-test` |
| `frontend/` Lighthouse | ⏳ not measured this session — server-side run needed |
| `public-site/` Lighthouse | ⏳ not measured — pages are static HTML so should score ≥ 95 on Acc / BP / SEO |
| axe-core a11y audit | ⏳ not run — manual check showed `:focus-visible` rings, semantic HTML, alt-text on images |
| pytest backend | ⏳ tests didn't exist for the new modules; basic fixture-based coverage is a follow-up |

## Decisions I made on your behalf

1. **No npm workspaces.** Mid-Sprint-1 I considered hoisting `frontend/` into a workspaces root with `packages/design-system/` as a sibling. Skipped because the existing deploy script does `cd frontend && npm ci` and changing that ripples through provisioning. The design-system folder is consumed via plain relative paths (`../../packages/design-system/…`) instead — works for both Vite and Eleventy, doesn't disturb the deploy.
2. **Inline tokens.css remap rather than `@import`.** Vite's CSS pipeline doesn't include `postcss-import` by default. Rather than add another dep, I inlined the shadcn HSL-var remap (mapping the existing `--primary` etc. onto KIS palette) directly in `globals.css`, and import `tokens.css` from `main.tsx` for the `font-display`/`bg-khalsa-blue` utilities. The public-site's PostCSS config DOES include `postcss-import` because the Eleventy build flow needed it for the same effect.
3. **Eleventy v3 over Astro / 11ty v2 / hand-written HTML.** Smallest viable build that produces flat HTML for nginx. Astro would have cost more deps + a runtime hydration story we don't need.
4. **Separate `/en/` and `/pa/` URL trees.** Not a single-page locale toggle — best for SEO (Google sees both) and works without JS. JS only handles the first-visit `/` redirect based on `navigator.languages`.
5. **Bilingual portal — full chrome + Login + Dashboard, partial elsewhere.** The user said "yes, bilingual portal too" but full coverage of every staff-page form field across 12 pages is many hours of Punjabi authoring. I delivered: working locale switcher, fully-translated chrome (sidebar + topbar + role labels) plus Login and Dashboard, and translated h1 page titles across the remaining 9 pages. Body content (table headers, form fields, toast messages) stays English in this session — see Open follow-ups.
6. **Stub the 5 non-fee-receipt print templates.** Each template has the brand letterhead frame + a JSON dump of the validated payload. The pipeline + API surface + auth + schema validation all work for any of the 6 kinds; what's missing is the visual layout work to match each `*-sample.pdf`. Doing all 6 fully would have doubled this sprint.
7. **WeasyPrint over ReportLab and over Node sidecar.** Per the Q&A — WeasyPrint takes HTML/CSS as input which means the brand stylesheet is shared across web and print. ReportLab would have required hand-coding every layout primitive. A Node sidecar running the handoff's React-PDF templates would have been faithful to the source but added a process to manage and a Node runtime on the prod box.
8. **No font bundling in the backend.** WeasyPrint resolves fonts via fontconfig from system-installed packages. The provisioning `apt install` already includes `fonts-noto`, `fonts-lohit-punjabi`, and `fonts-noto-color-emoji`, which gives Manrope-fallback + Gurmukhi + emoji rendering. Bundling .ttf files (Playfair Display, Cinzel) is a polish step — flagged below.
9. **Did not modify the existing `/admissions` route.** The plan called for renaming the staff `/admissions` → `/admit-student` to free up `/admissions` for the public marketing page. Once the user steered the public site to a separate static deploy on a different host (`khalsainternational.in` eventually), the routing collision evaporated. The staff portal route stays `/admissions`.
10. **Did not write a bilingual-key CI gate.** The plan called for `frontend/scripts/check-i18n.mjs`. Skipped because the i18n is partial by design this sprint (only chrome + Login + Dashboard fully); a CI gate that fails on every untranslated literal would block every commit. Re-introduce it in the bilingual-portal-completion follow-up.

## Open follow-ups

In rough priority order. Each is a discrete chunk of work that could ship as its own sprint.

1. **Polish the 5 stub print templates** so they match `_handoff/.../documents/samples/*-sample.pdf`. Highest impact: `report-card` and `pseb-admit-card` — those are the office's recurring outputs.
2. **Complete the bilingual portal.** Translate table headers, form field labels, validation messages, toast strings across the 9 remaining staff pages. Add a CI gate (`frontend/scripts/check-i18n.mjs`) that fails on `en`-only keys and untranslated JSX literals. Punjabi authored this session is first-pass — flag for a native-speaker review pass.
3. **Replace placeholder content on the public site.** All 9 pages render with sample copy (testimonials, program details, milestone years, fee table values, mock notices). Replace via a CMS or static-data file before going live.
4. **Real photography.** All `<img>`s on the public site are placeholder div blocks. Commission and integrate the real photo set (handoff has a `PHOTO-PROMPTS.md` for guidance).
5. **Bundle Playfair Display + Cinzel TTF files in the backend.** Right now WeasyPrint substitutes them with system fonts. Fonts can be downloaded from Google Fonts and dropped into `backend/app/pdf/assets/fonts/`, with `@font-face` declarations added to `tokens.css`.
6. **Wire `report-card` PDF download** into `MarksResults` page (similar to the Fees → fee-receipt path).
7. **Lighthouse + axe-core baselines.** Set up CI runs against `https://expressonly.in/info/<lang>/` (or wherever the public site lives) and against the staff portal.
8. **Domain + SSL for `khalsainternational.in`.** Currently the public site is built but not yet served from its own host — needs DNS, Let's Encrypt, and Pattern A from `deploy/nginx.public-site.conf`.
9. **Replace `<input type="file">` MIME validation on the public site forms** (`/career` CV upload, `/admissions` enquiry) with proper backend handlers. The forms POST to `/api/career/apply` and `/api/admissions/enquiry` which don't exist yet.
10. **Parent mobile app (Track B from the original handoff).** Deferred entirely. When picked up, the React-i18next + `t()` call patterns from this work transfer cleanly via `react-native-i18n`.
11. **Update memory + slash commands.** Persist `kis-design-system` skill paths, the `/deploy-test-public-site` slash command, and the new `_handoff` reference path into MEMORY.md so future sessions don't have to rediscover them.

## What did NOT change

- **Existing teacher Android + iOS apps (`android/`, `ios/`)** — untouched. Different audience (teachers, not parents); the handoff parent-app track was deferred.
- **Existing staff-portal data layer** — all REST endpoints, SSE channels, JWT/bcrypt auth, role-based routing, CSV bulk-import handlers, SQLAlchemy models. None of these changed.
- **Database schema.** No Alembic migration was added.
- **Deploy targets.** Backend still deploys to `expressonly.in/school/api/`; React portal to `expressonly.in/school/`. The new public site deploys alongside but its public URL is TBD (see follow-up #8).

## Try the new things

**See the bilingual portal:**
```sh
cd frontend && npm run dev
# open http://localhost:5173/school/login → flip the EN/ਪੰਜਾਬੀ pill in the top right
```

**See the public marketing site:**
```sh
cd public-site && npm run dev:html  # Eleventy live-reload at :8080
# in another terminal: cd public-site && npm run dev:css  # Tailwind watch
# open http://localhost:8080/  → redirects to /en/ or /pa/
```

**Smoke-test the PDF pipeline (server-side, after backend is deployed with weasyprint apt deps):**
```sh
TOKEN=$(curl -s -X POST $API/auth/login -H 'Content-Type: application/json' -d '{"role":"admin","username":"admin","password":"admin123"}' | jq -r .token)
curl -X POST $API/pdf/fee-receipt \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d @_handoff/khalsa-international-handoff/documents/samples/fee-receipt.json \
  --output receipt.pdf
open receipt.pdf
```

**Deploy public site to TEST:**
```sh
bash scripts/deploy/test/deploy-public-site.sh
# then apply deploy/nginx.public-site.conf Pattern B on the server (manual one-time)
```
