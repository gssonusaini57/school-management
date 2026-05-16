# SEO Checklist

Per page: title, description, OG image, Twitter card, canonical, hreflang `en` ↔ `pa`, JSON-LD schema.

## Per-page meta (English values; Punjabi values mirror via i18n)

| Page | Title | Description (≤155 chars) | Schema.org |
|---|---|---|---|
| Home | Khalsa International Sr. Sec. School — Patiala, Punjab | PSEB-affiliated co-ed school in Jalalabad, Patiala. Vidya · Vichar · Seva. Admissions open 2026–27. | EducationalOrganization |
| About | About — Khalsa International | Serving Patiala since 2005. Mission, vision, leadership. | AboutPage |
| Academics | Academics — Khalsa International | Six programs from Foundation Play to Senior Secondary streams. PSEB-aligned curriculum. | EducationalOrganization > hasCourse[] |
| Admissions | Admissions 2026–27 — Khalsa International | Apply now for Nursery to Class XII. Walk-in counselling, fee structure, application form. | EducationalOrganization > admissionApplication |
| Notices | Notices — Khalsa International | Latest exam, fee, admission and event notices from KIS Patiala. | CollectionPage |
| Gallery | Gallery — Khalsa International | Photos from school life, events, sports and academics. | ImageGallery |
| Contact | Contact — Khalsa International | Address, phone, email and directions to KIS Jalalabad, Patiala. | ContactPage |
| Career | Careers — Khalsa International | Open positions for teachers and staff at KIS Patiala. | JobPosting (per opening) |

## OG image rules

- 1200×630, Khalsa Blue background, crest + school name + page-specific kicker.
- Punjabi locale uses a Punjabi kicker.
- Generated at build via `/og?title=...&locale=...` Next.js route.

## JSON-LD example (Home)

```json
{
  "@context": "https://schema.org",
  "@type": "EducationalOrganization",
  "name": "Khalsa International Senior Secondary School",
  "alternateName": "ਖ਼ਾਲਸਾ ਇੰਟਰਨੈਸ਼ਨਲ ਸੀਨੀਅਰ ਸੈਕੰਡਰੀ ਸਕੂਲ",
  "foundingDate": "2005",
  "address": { "@type": "PostalAddress", "addressLocality": "Jalalabad", "addressRegion": "Patiala, Punjab", "addressCountry": "IN" },
  "telephone": "+91-93563-31762",
  "url": "https://www.khalsainternational.in",
  "logo": "https://www.khalsainternational.in/logo.png"
}
```

## Sitemap & robots

- `/sitemap.xml` auto-generated, includes both locales.
- `/robots.txt` allows all, points to sitemap.
- Lighthouse SEO ≥ 95.
