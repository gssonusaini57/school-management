import { useTranslation } from "react-i18next";
import type { PdfTemplate, ReportLayout, ResultScope } from "@/types/api";

// Term labels the server reads as a scope for templates made before scopes existed
// (scope_from_term in app/services/results.py). Keep the three sets in step with it.
const TERM1_LABELS = new Set(["term i", "term 1", "term-1", "term1", "t1", "1", "first", "first term", "1st term"]);
const TERM2_LABELS = new Set(["term ii", "term 2", "term-2", "term2", "t2", "2", "second", "second term", "2nd term"]);
const ANNUAL_LABELS = new Set(["", "annual", "final", "full year", "year"]);

/** The scope a term label stands for, or null when the server doesn't recognise the label. */
export function scopeFromTerm(term: string | null | undefined): ResultScope | null {
  const label = (term ?? "").trim().toLowerCase().split(/\s+/).filter(Boolean).join(" ");
  if (TERM1_LABELS.has(label)) return "term1";
  if (TERM2_LABELS.has(label)) return "term2";
  if (ANNUAL_LABELS.has(label)) return "annual";
  return null;
}

/** The scope a report-card template prints: its own, else the one its term label stands for. */
export function templateScope(template: Pick<PdfTemplate, "scope" | "term">): ResultScope | null {
  return template.scope ?? scopeFromTerm(template.term);
}

/** Translated names for result scopes and report-card layouts. */
export function useReportCardLabels() {
  const { t } = useTranslation();

  const scopeLabel = (scope: ResultScope | null | undefined): string => {
    switch (scope) {
      case "term1":
        return t("portal.results.term1", "Term 1");
      case "term2":
        return t("portal.results.term2", "Term 2");
      case "annual":
        return t("portal.results.annual", "Annual");
      default:
        return "—";
    }
  };

  const layoutLabel = (layout: ReportLayout | null | undefined): string =>
    layout === "components"
      ? t("portal.templates.layoutComponents", "Per-exam columns")
      : t("portal.templates.layoutSummary", "Summary — one row per subject");

  /** One line on what a layout prints, for the given scope. */
  const layoutHint = (layout: ReportLayout, scope: ResultScope): string => {
    if (layout === "summary") {
      return t("portal.templates.layoutSummaryHint", "Marks, maximum and grade for each subject.");
    }
    return scope === "annual"
      ? t("portal.templates.layoutComponentsHintAnnual", "Term 1 and Term 2 columns for each subject, then total and grade.")
      : t("portal.templates.layoutComponentsHint", "A column for each exam (P.T. First, P.T. Second, Semester …), then total and grade.");
  };

  return { scopeLabel, layoutLabel, layoutHint };
}
