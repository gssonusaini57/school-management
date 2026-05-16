# Information Architecture — www.khalsainternational.in

## Sitemap

- `/` — Home
- `/about` — About
- `/academics` — Academics (overview + 6 program sub-anchors)
- `/admissions` — Admissions (process, fees, downloadable form)
- `/notices` — Notices (filterable by category)
- `/notices/[slug]` — Single notice
- `/gallery` — Gallery (year-tabbed)
- `/contact` — Contact (map, phone, form)
- `/career` — Careers (job openings, application form)
- `/parent-portal` — Parent Portal (sign-in stub linking to mobile app deep-link)
- `/privacy` · `/terms` — Legal

## Locale routing

`next-intl` with `localePrefix: 'always'`. URLs:
- `/en/admissions` ↔ `/pa/admissions`
- Default redirect: `/` → `/pa` if Accept-Language matches `pa`, else `/en`.
- `hreflang` tags pair every page across both locales.

## Nav structure

Primary nav (desktop, in order): Home · About · Academics · Admissions · Notices · Gallery · Contact. Right-aligned: Language switcher · "Apply now" CTA.

Footer columns: Quick links / Contact / Resources / Social.

## Information density

The home page carries 9 sections. Sub-pages keep depth ≤ 1 (no nested sub-nav). Notices index supports pagination at 12 per page.

## Page priorities

1. **Admissions** — most-visited by intent. Fee table, downloadable form, application steps, contact CTA.
2. **Academics** — most-visited by exploration. Six program cards link to anchors with curriculum + faculty + extracurriculars.
3. **Home** — first impression. Hero + values + principal letter + admissions CTA must communicate identity in < 1 scroll.
