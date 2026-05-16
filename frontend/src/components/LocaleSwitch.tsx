import { useTranslation } from "react-i18next";
import { cn } from "@/lib/utils";

/**
 * Two-pill locale toggle for the portal topbar. Persistence + html[lang]
 * sync are handled inside lib/i18n.ts on the languageChanged event.
 */
export function LocaleSwitch({ className }: { className?: string }) {
  const { i18n } = useTranslation();
  const set = (lng: "en" | "pa") => i18n.language !== lng && i18n.changeLanguage(lng);

  return (
    <div
      role="group"
      aria-label="Language"
      className={cn(
        "inline-flex items-center rounded-full border border-input bg-background p-0.5 text-xs font-semibold",
        className
      )}
    >
      <button
        type="button"
        onClick={() => set("en")}
        aria-pressed={i18n.language === "en"}
        lang="en"
        className={cn(
          "px-2.5 py-1 rounded-full transition-colors",
          i18n.language === "en" ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-accent"
        )}
      >
        EN
      </button>
      <button
        type="button"
        onClick={() => set("pa")}
        aria-pressed={i18n.language === "pa"}
        lang="pa"
        className={cn(
          "px-2.5 py-1 rounded-full transition-colors",
          i18n.language === "pa" ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-accent"
        )}
      >
        ਪੰਜਾਬੀ
      </button>
    </div>
  );
}
