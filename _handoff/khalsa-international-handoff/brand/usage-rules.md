# Brand Usage Rules

These rules are absolute. The crest, the wordmark and the colour system are how Khalsa International is recognized — they are not decorations to be remixed.

## 1. Logo

### Approved lockups
- `crest-full.svg` — crest + wordmark + tagline (use on hero areas, letterheads, certificates).
- `crest-mark.svg` — crest only (use as favicon, app icon, social DP, watermarks).
- `wordmark-en.svg` — "Khalsa International / SR. SEC. SCHOOL" (use when crest is too small to render correctly, e.g. mobile nav at < 24px).
- `wordmark-pa.svg` — Gurmukhi wordmark (use on Punjabi-first surfaces).

### Clear space
Reserve a clear-space margin equal to **the cap height of "K"** in the wordmark on all four sides of the lockup. Nothing — including text, photos, or buttons — may enter that zone.

### Minimum sizes
| Use | Minimum |
|---|---|
| Print | 18mm wide for crest-full; 12mm for crest-mark |
| Digital | 96px wide for crest-full; 32px for crest-mark; 24px for wordmark only |
| Favicon | 16×16 (use `favicon.ico` — already pixel-hinted) |

### On photographs
Use `crest-full.svg` reversed on dark imagery only when the imagery has ≥ 50% coverage at L\* 30 or darker (validated in `accessibility/color-contrast-report.md`). Otherwise place the crest on a Vasant Cream or White panel.

### Don'ts
- Do **not** recolor the crest. The blue/gold/red palette is locked.
- Do **not** rotate, skew, or stretch the crest.
- Do **not** outline the wordmark.
- Do **not** apply drop-shadows, glows, or bevel effects to the lockup.
- Do **not** combine the crest with another logo at equal weight (co-branding requires the school crest to be larger and on the left).
- Do **not** redraw the Khanda. Use the vector provided.

## 2. Colour

Use only the six brand colors and the neutral scale defined in `design-tokens/tokens.json`. Semantic colors (success, warning) are derived — do not introduce new ones.

### Pairings
- **Khalsa Blue on Vasant Cream** — primary headline pairing.
- **Royal Gold on Deep Indigo** — honors, certificates, awards.
- **Sangat Red** — used **only** for ribbon, alerts and the tricolor band. Never as a body text color.
- **Ink on White** — body text, default.
- **White on Khalsa Blue** — buttons, dark masthead.

### Do not
- Tint the brand blue lighter than 80% to use as "background blue". Use Vasant Cream instead.
- Place body text on Royal Gold (fails contrast).
- Use Sangat Red over Khalsa Blue (vibrates).

## 3. Typography

| Surface | Font | Weight | Notes |
|---|---|---|---|
| Display headlines | Playfair Display | 700–800 | Tight letter-spacing (-0.02em). |
| Crest caps lockup | Cinzel | 600 | Always small caps, letter-spacing 0.32em. |
| Body / UI | Manrope | 400 / 600 / 700 | Default everywhere. |
| Punjabi (Gurmukhi) | Noto Sans Gurmukhi | 400 / 600 | Line-height 1.5. Never substitute. |
| Numbers in tabular contexts | Manrope, `font-variant-numeric: tabular-nums` | 600 | Receipts, payslips, marksheets. |

Never substitute Inter, Roboto, Arial or system stacks for any of these. Always include the font @import or @font-face at the document root.

## 4. Photography

- Real, candid, classroom-shot. No stock-photo schoolchildren.
- Aim for natural light and Punjabi context (uniforms, dastar, dupatta, school crest visible).
- Process to a slightly warm cast that aligns with Vasant Cream — see `brand/photography-treatment.md` (to be created post-shoot).
- Always include alt text in **both** languages.

## 5. Iconography

- Use the SVG set in `assets/icons/`. Single weight (1.5px stroke), 24px box.
- No emoji in product UI.
- Do not mix in Material / Lucide / Heroicons. The set is final and will grow when commissioned.

## 6. Co-branding

When the school appears alongside another organization:
- Khalsa International crest is on the left at 100% scale.
- Co-brand mark is on the right, sized so its **x-height** matches our wordmark x-height (visual weight, not raw px).
- A 1.5px Sangat Red vertical rule separates the two (height = max of either lockup).
