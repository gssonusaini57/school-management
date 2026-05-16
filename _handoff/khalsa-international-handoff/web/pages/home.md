# Home (`/`)


## Sections (in order)

1. **HeroBlock** — `web.home.heroEyebrow`, `heroTitle`, `heroBody`, CTAs `ctaApply` + `ctaVisit`. Image right.
2. **StatsStrip** — 4 `StatTile`s (Students 1,240 / Faculty 78 / PSEB result 98% / Years serving 19) + 1 award badge. Tokens `web.home.stats.*`.
3. **Why KIS** — 4 `Card`s in a 2×2 grid: Vidya / Vichar / Seva / Roots (`web.home.values.*`).
4. **PrincipalLetter** organism — portrait + `web.home.principal.body` (en + pa).
5. **ProgramGrid** — 6 `ProgramCard`s. Title from `web.home.programsTitle`.
6. **GalleryStrip** — 7 candid photos. Title from `web.home.lifeTitle`.
7. **VoicesGrid** — 6 `TestimonialCard`s. Title from `web.home.voicesTitle`.
8. **NoticeBoard** — latest 5. Title from `web.home.noticesTitle`. "View all" → `/notices`.
9. **AdmissionsCTA** — full-bleed brand band. Title `web.home.admissionsCtaTitle`, body `admissionsCtaBody`, primary CTA → `/admissions`, secondary → `/contact`.

## Composition tree

```
<SiteHeader />
<HeroBlock />
<StatsStrip />
<ValueProps />            ← composition of <Card>×4
<PrincipalLetter />
<ProgramGrid />
<GalleryStrip />
<VoicesGrid />
<NoticeBoard limit={5} />
<AdmissionsCTA />
<SiteFooter />
```

## Responsive

- 2xl/xl: hero 12-col with text 6 / image 6.
- lg: same, with reduced font scale.
- md: hero stacks; stats 2×2; values 2×2; programs 2-col.
- sm: everything single-column; gallery becomes horizontal scroll-snap.

## Static copy slots — character limits

| Slot | Max chars |
|---|---|
| heroTitle | 70 |
| heroBody | 180 |
| stat label | 20 |
| value title | 30 |
| value body | 90 |
| program card body | 100 |
| testimonial quote | 180 |

## SEO

See `seo-checklist.md`. Title and description per locale.

