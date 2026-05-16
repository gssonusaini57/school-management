const fs = require("node:fs");
const path = require("node:path");

const HANDOFF_STRINGS = JSON.parse(
  fs.readFileSync(
    path.join(__dirname, "..", "_handoff", "khalsa-international-handoff", "i18n", "strings.json"),
    "utf8"
  )
);

// Local additions live next to the handoff source, in the same shape
// `{ namespace: { key: { en, pa } } }`. Used for page-specific copy that
// isn't part of the canonical handoff package.
let EXTRA_STRINGS = {};
const extraPath = path.join(__dirname, "i18n", "extra-strings.json");
if (fs.existsSync(extraPath)) {
  EXTRA_STRINGS = JSON.parse(fs.readFileSync(extraPath, "utf8"));
}

function deepMerge(a, b) {
  const out = { ...a };
  for (const k of Object.keys(b)) {
    const av = out[k];
    const bv = b[k];
    const isLeaf = (v) =>
      v && typeof v === "object" && "en" in v && "pa" in v && Object.keys(v).length === 2;
    if (
      av && typeof av === "object" && !Array.isArray(av) && !isLeaf(av) &&
      bv && typeof bv === "object" && !Array.isArray(bv) && !isLeaf(bv)
    ) {
      out[k] = deepMerge(av, bv);
    } else {
      out[k] = bv;
    }
  }
  return out;
}

const STRINGS = deepMerge(HANDOFF_STRINGS, EXTRA_STRINGS);

/**
 * `t("common.applyNow", "en")` → "Apply now"
 * `t("common.applyNow", "pa")` → "ਹੁਣੇ ਅਪਲਾਈ ਕਰੋ"
 *
 * Falls back to `en` if the key doesn't exist for the requested locale, then
 * to the literal key so missing entries are visible during development.
 */
function t(key, lang) {
  const parts = key.split(".");
  let node = STRINGS;
  for (const p of parts) {
    if (!node || typeof node !== "object" || !(p in node)) return `[${key}]`;
    node = node[p];
  }
  if (node && typeof node === "object" && "en" in node && "pa" in node) {
    return node[lang] ?? node.en;
  }
  return `[${key}]`;
}

module.exports = function (eleventyConfig) {
  // Brand SVGs from the design-system, copied into dist/brand/.
  eleventyConfig.addPassthroughCopy({
    "../packages/design-system/brand": "brand",
  });

  // Local public/ folder is rsynced verbatim into dist/.
  eleventyConfig.addPassthroughCopy({ public: "/" });

  // CSS + JS folders inside dist/ are produced by the Tailwind/postcss build,
  // so just leave dist/css/ alone (Eleventy clears unknown files by default
  // when using addPassthroughCopy strategy=copy; we keep that off).
  eleventyConfig.setServerPassthroughCopyBehavior("passthrough");

  // i18n filter: {{ "common.applyNow" | t(lang) }}
  eleventyConfig.addFilter("t", function (key, lang) {
    return t(key, lang || "en");
  });

  // Mark a nav link as active when its slug matches the current page.
  eleventyConfig.addFilter("isCurrent", function (page, slug) {
    if (!page || !page.url) return false;
    if (slug === "home") {
      return page.url.endsWith("/en/") || page.url.endsWith("/pa/") || page.url === "/";
    }
    return page.url.includes(`/${slug}`);
  });

  // The opposite-locale URL for the language-switch button.
  eleventyConfig.addFilter("flipLocale", function (url) {
    if (!url) return "/";
    if (url.startsWith("/en/")) return url.replace(/^\/en\//, "/pa/");
    if (url.startsWith("/pa/")) return url.replace(/^\/pa\//, "/en/");
    return url;
  });

  return {
    dir: {
      input: "src",
      output: "dist",
      includes: "_includes",
      data: "_data",
    },
    templateFormats: ["njk", "md", "html"],
    htmlTemplateEngine: "njk",
    markdownTemplateEngine: "njk",
  };
};
