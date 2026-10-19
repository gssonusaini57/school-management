import { useTranslation } from "react-i18next";
import { RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import { reloadWithCacheBust, useUpdateWaiting } from "@/lib/version";

/**
 * A newer build is deployed while this tab has unsaved edits, so the automatic
 * reload (lib/version.ts) waits for them to be saved. Says so without blocking anything.
 */
export function UpdateBanner() {
  const { t } = useTranslation();
  const waiting = useUpdateWaiting();
  if (!waiting) return null;
  return (
    <div
      role="status"
      className="fixed bottom-4 left-4 right-4 z-50 flex flex-wrap items-center gap-3 rounded-md border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-900 shadow-lg sm:right-auto sm:max-w-md print:hidden"
    >
      <span className="min-w-0 flex-1">
        {t("portal.common.updateWaiting", "A new version of the portal is available. Save your changes, then reload the page.")}
      </span>
      <Button variant="outline" size="sm" onClick={() => reloadWithCacheBust()}>
        <RefreshCw /> {t("portal.common.reloadPage", "Reload the page")}
      </Button>
    </div>
  );
}
