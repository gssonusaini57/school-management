import { useId, useState } from "react";
import { Link } from "react-router-dom";
import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { FileText, Layers, Settings2, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { templateResolveQuery } from "@/lib/pdf";
import { cn, formatDate } from "@/lib/utils";
import type { PdfTemplate, PdfTemplateBulkCreateResult, ReportLayout, ResultScope } from "@/types/api";
import { ReportCardRoster } from "./ReportCardRoster";
import { useReportCardLabels } from "./labels";

const LAYOUTS: ReportLayout[] = ["summary", "components"];

/**
 * The "Report cards" tab of the Results page: finds the report-card template for
 * the chosen class, session and scope and shows its roster, or offers admins to
 * create the template (for this class or every class) when there is none yet.
 */
export function ReportCardsTab({ cls, session, scope }: { cls: string; session: string; scope: ResultScope }) {
  const { t } = useTranslation();
  const { isAdmin } = useAuth();
  const { scopeLabel, layoutLabel } = useReportCardLabels();

  const resolveQ = useQuery({ ...templateResolveQuery(cls, session, scope), enabled: !!cls && !!session });

  if (!cls || !session) {
    return (
      <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
        <FileText className="mx-auto mb-2 h-6 w-6" aria-hidden />
        {!cls
          ? t("portal.reportCards.pickClass", "Pick a class to see its report cards.")
          : t("portal.reportCards.pickSession", "Pick a session to see its report cards.")}
      </div>
    );
  }

  if (resolveQ.isPending) {
    return (
      <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Spinner /> {t("portal.reportCards.resolving", "Looking for the report-card template…")}
      </div>
    );
  }

  if (resolveQ.isError && resolveQ.data === undefined) {
    return (
      <div role="alert" className="flex flex-wrap items-center gap-2 rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
        <TriangleAlert className="h-4 w-4 shrink-0" />
        <span>
          {t("portal.reportCards.resolveError", "Couldn't check for a report-card template.")} {apiError(resolveQ.error)}
        </span>
        <Button variant="outline" size="sm" className="ml-auto" onClick={() => void resolveQ.refetch()}>
          {t("portal.common.tryAgain", "Try again")}
        </Button>
      </div>
    );
  }

  const template = resolveQ.data ?? null;
  if (!template) {
    if (isAdmin) return <CreateTemplatePanel cls={cls} session={session} scope={scope} />;
    return (
      <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
        <FileText className="mx-auto mb-2 h-6 w-6" aria-hidden />
        <p className="font-medium text-foreground">
          {t("portal.reportCards.noTemplate", "No report-card template for {{cls}} · {{scope}} yet.", { cls, scope: scopeLabel(scope) })}
        </p>
        <p className="mt-1">{t("portal.reportCards.askAdmin", "Ask an admin to create it.")}</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-md border bg-card px-4 py-3 text-sm shadow-sm">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
          <FileText className="h-4 w-4 shrink-0 text-khalsa-blue" aria-hidden />
          {/* An older template without a scope of its own was resolved by its term label, as this scope. */}
          <span className="font-semibold text-deep-indigo">{scopeLabel(template.scope ?? scope)}</span>
          <Badge variant="info">{layoutLabel(template.layout)}</Badge>
          <span className="text-muted-foreground">
            {t("portal.reportCards.versionInfo", "Version {{version}} · updated by {{name}} on {{date}}", {
              version: template.version,
              name: template.updated_by || "—",
              date: formatDate(template.updated_at),
            })}
          </span>
        </div>
        {isAdmin && (
          <Button asChild variant="outline" size="sm">
            <Link to={`/templates/${template.id}`}>
              <Settings2 /> {t("portal.reportCards.cardSettings", "Card settings")}
            </Link>
          </Button>
        )}
      </div>
      <ReportCardRoster template={template} />
    </div>
  );
}

function CreateTemplatePanel({ cls, session, scope }: { cls: string; session: string; scope: ResultScope }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { scopeLabel, layoutLabel, layoutHint } = useReportCardLabels();
  const [layout, setLayout] = useState<ReportLayout>("summary");
  const radioGroup = useId();

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["pdf-template-resolve"] });
    qc.invalidateQueries({ queryKey: ["pdf-templates"] });
  };
  const onFailed = (e: unknown) => {
    toast(apiError(e), "error");
    // 409: it was created meanwhile (by a colleague, say), so show it.
    if (axios.isAxiosError(e) && e.response?.status === 409) refresh();
  };

  const createOne = useMutation({
    mutationFn: () =>
      api
        .post<PdfTemplate>("/pdf/templates", { kind: "report-card", class_name: cls, session, scope, layout, data: {} })
        .then((r) => r.data),
    onSuccess: (created) => {
      qc.setQueryData(templateResolveQuery(cls, session, scope).queryKey, created);
      refresh();
      toast(t("portal.reportCards.templateCreated", "Report-card template created for {{cls}}.", { cls }), "success");
    },
    onError: onFailed,
  });

  const createAll = useMutation({
    mutationFn: () =>
      api
        .post<PdfTemplateBulkCreateResult>("/pdf/templates/bulk-create", {
          kind: "report-card",
          session,
          scope,
          layout,
          class_names: null, // every class
          data: {},
        })
        .then((r) => r.data),
    onSuccess: (res) => {
      refresh();
      const created = t("portal.templates.created", "{{n}} created", { n: res.created.length });
      const skipped = t("portal.templates.skipped", "{{n}} skipped", { n: res.skipped.length });
      toast(`${created} · ${skipped}`, res.created.length ? "success" : "warning");
    },
    onError: onFailed,
  });

  const busy = createOne.isPending || createAll.isPending;
  const onCreateAll = () => {
    const ok = window.confirm(
      t(
        "portal.reportCards.createAllConfirm",
        "Create {{scope}} report-card templates for every class in {{session}}? Classes that already have one are skipped.",
        { scope: scopeLabel(scope), session },
      ),
    );
    if (ok) createAll.mutate();
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>
          {t("portal.reportCards.setUpTitle", "Set up report cards for {{cls}} · {{scope}}", { cls, scope: scopeLabel(scope) })}
        </CardTitle>
        <CardDescription>
          {t(
            "portal.reportCards.setUpHint",
            "There is no report-card template for this class, session and term yet. Pick how marks are laid out; signatures and other card settings can be changed later.",
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">{t("portal.templates.layout", "Layout")}</legend>
          <div className="grid gap-2 sm:grid-cols-2">
            {LAYOUTS.map((value) => (
              <label
                key={value}
                className={cn(
                  "flex cursor-pointer items-start gap-3 rounded-md border p-3 transition-colors has-[:focus-visible]:ring-2 has-[:focus-visible]:ring-ring",
                  layout === value ? "border-primary bg-primary/5" : "hover:bg-muted/50",
                )}
              >
                <input
                  type="radio"
                  name={radioGroup}
                  value={value}
                  checked={layout === value}
                  onChange={() => setLayout(value)}
                  className="mt-0.5 h-4 w-4 accent-primary"
                />
                <span>
                  <span className="block text-sm font-semibold">{layoutLabel(value)}</span>
                  <span className="mt-0.5 block text-xs text-muted-foreground">{layoutHint(value, scope)}</span>
                </span>
              </label>
            ))}
          </div>
        </fieldset>

        <div className="flex flex-wrap gap-2">
          <Button onClick={() => createOne.mutate()} disabled={busy}>
            {createOne.isPending ? <Spinner /> : <FileText />} {t("portal.templates.createForClass", "Create for {{cls}}", { cls })}
          </Button>
          <Button variant="outline" onClick={onCreateAll} disabled={busy}>
            {createAll.isPending ? <Spinner /> : <Layers />} {t("portal.templates.createForAll", "Create for all classes")}
          </Button>
        </div>
        <p className="text-xs text-muted-foreground">
          {t(
            "portal.reportCards.createAllHint",
            "“Create for all classes” makes one {{scope}} template per class for {{session}} with this layout, and skips classes that already have one.",
            { scope: scopeLabel(scope), session },
          )}
        </p>
      </CardContent>
    </Card>
  );
}
