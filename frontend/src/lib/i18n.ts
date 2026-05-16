import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "../../../packages/design-system/i18n/en.json";
import pa from "../../../packages/design-system/i18n/pa.json";
import portalEn from "../../../packages/design-system/i18n/portal-en.json";
import portalPa from "../../../packages/design-system/i18n/portal-pa.json";

export const SUPPORTED_LOCALES = ["en", "pa"] as const;
export type Locale = (typeof SUPPORTED_LOCALES)[number];

const STORAGE_KEY = "kis.locale";

function detectInitialLocale(): Locale {
  const stored = typeof window !== "undefined" ? localStorage.getItem(STORAGE_KEY) : null;
  if (stored === "en" || stored === "pa") return stored;
  return "en";
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      // The two stores merge cleanly because the handoff strings use the
      // top-level keys `common`, `web`, `mobile`, while portal strings live
      // entirely under `portal`.
      en: { translation: { ...en, ...portalEn } },
      pa: { translation: { ...pa, ...portalPa } },
    },
    lng: detectInitialLocale(),
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    returnNull: false,
  });

i18n.on("languageChanged", (lng) => {
  if (typeof window !== "undefined") {
    localStorage.setItem(STORAGE_KEY, lng);
    document.documentElement.lang = lng;
  }
});

if (typeof document !== "undefined") {
  document.documentElement.lang = i18n.language;
}

export default i18n;
