/**
 * Site-wide config consumed by templates as `{{ site.<key> }}`.
 *
 * Keep simple values here and pull translatable copy from the i18n strings via
 * the `t` filter (`{{ "common.schoolName" | t(lang) }}`).
 */

// URL prefix the static site is mounted under in nginx. Keep the trailing
// slash off — templates concatenate it as `{{ site.basePath }}/{{ lang }}/...`.
// Build-time configurable via SITE_BASE_PATH (set by scripts/deploy/<env>/env.sh):
// TEST serves under "/school", PROD serves at the apex root (empty string "").
// `??` keeps the default only for null/undefined, so an explicit "" is honoured.
const basePath = process.env.SITE_BASE_PATH ?? "/school";

module.exports = {
  domain: "kisschool.in",
  baseUrl: "https://www.kisschool.in",
  basePath,
  // Pages in the order they appear in the site header. Each entry has a slug
  // (used to compute /<lang>/<slug>/) and an i18n key for its label.
  nav: [
    { slug: "", labelKey: "web.nav.home" },
    { slug: "about", labelKey: "web.nav.about" },
    { slug: "academics", labelKey: "web.nav.academics" },
    { slug: "admissions", labelKey: "web.nav.admissions" },
    { slug: "notices", labelKey: "web.nav.notices" },
    { slug: "gallery", labelKey: "web.nav.gallery" },
    { slug: "contact", labelKey: "web.nav.contact" },
  ],
  // Footer columns.
  footer: {
    quickLinks: ["", "about", "academics", "admissions", "career"],
    resources: ["notices", "gallery", "contact"],
  },
  // Brand crest URLs — already prefixed with basePath so templates can use them
  // verbatim (`<img src="{{ site.crestMark }}">`). PNG used over SVG: the SVG
  // has a font-fallback issue on the "AFFILIATED TO P.S.E.B." banner ribbon
  // (CorelDRAW font isn't on Linux), but the PNG is a pixel-perfect render
  // of the original CDR.
  crestMark:  basePath + "/brand/crest-mark.png",     // 256px — favicon, header
  crestFull:  basePath + "/brand/crest-full.png",     // 1024px — hero, footer
  wordmarkEn: basePath + "/brand/wordmark-en.svg",
  wordmarkPa: basePath + "/brand/wordmark-pa.svg",
  cssUrl:     basePath + "/css/site.css",
};
