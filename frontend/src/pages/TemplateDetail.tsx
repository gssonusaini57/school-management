import { useEffect, useId, useMemo, useState, type ReactNode } from "react";
import { Link, useParams } from "react-router-dom";
import axios from "axios";
import { useMutation, useQuery, useQueryClient, type QueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  ArrowLeft, Eye, FileDown, FileText, Info, Plus, RefreshCw, Save, ScrollText, Trash2, TriangleAlert, Undo2,
} from "lucide-react";
import { Badge, badgeVariants } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { NumberField } from "@/components/ui/number-field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toaster";
import { ReportCardRoster } from "@/components/report-cards/ReportCardRoster";
import { scopeFromTerm, templateScope, useReportCardLabels } from "@/components/report-cards/labels";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatNumber } from "@/lib/format";
import { useMeta } from "@/lib/meta";
import { REMARK_MAX, downloadCachedPdf, isClientError, openReportCardPreview, templateRosterQuery } from "@/lib/pdf";
import { useUnsavedChanges } from "@/lib/unsaved";
import { cn } from "@/lib/utils";
import type {
  Meta, PdfRenderResultRow, PdfStudentDataRow, PdfStudentRosterRow, PdfTemplate,
  ReportCardTemplateData, ReportLayout, ResultScope,
} from "@/types/api";

const LAYOUTS: ReportLayout[] = ["summary", "components"];
const SCOPES: ResultScope[] = ["term1", "term2", "annual"];
/** POST /pdf/templates/{id}/render takes at most this many students per request. */
const RENDER_CHUNK = 20;
const RENDER_TIMEOUT_MS = 5 * 60_000;

// ── Shared helpers ───────────────────────────────────────────────────────

function parseNumber(s: string): number | null {
  const v = s.trim();
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** Everything that shows this template or what its cards print. */
function invalidateTemplate(qc: QueryClient, id: number) {
  qc.invalidateQueries({ queryKey: ["pdf-template", id] });
  qc.invalidateQueries({ queryKey: ["pdf-templates"] });
  qc.invalidateQueries({ queryKey: ["pdf-roster", id] });
  qc.invalidateQueries({ queryKey: ["pdf-template-resolve"] });
  // The results table grades pass/fail with the class's report-card rule.
  qc.invalidateQueries({ queryKey: ["results"] });
}

/** Same shape as the server's pdf_filename(): <kind>_<class>_<roll>_<name>. */
function pdfFilename(kind: string, className: string, row: PdfStudentRosterRow): string {
  const safe = (s: string) => s.replace(/[^A-Za-z0-9.-]+/g, "-").replace(/^-+|-+$/g, "") || "x";
  return `${kind}_${safe(className)}${row.roll_no ? `_${safe(row.roll_no)}` : ""}_${safe(row.name)}`;
}

// ── Page ─────────────────────────────────────────────────────────────────

export default function TemplateDetail() {
  const { t } = useTranslation();
  const { id: idParam } = useParams<{ id: string }>();
  const id = Number(idParam);
  const validId = Number.isInteger(id) && id > 0;

  const tplQ = useQuery<PdfTemplate>({
    queryKey: ["pdf-template", id],
    queryFn: () => api.get<PdfTemplate>(`/pdf/templates/${id}`).then((r) => r.data),
    enabled: validId,
    retry: (failures, e) => !isClientError(e) && failures < 1,
  });

  if (!validId) return <TemplateUnavailable />;
  if (tplQ.data === undefined) {
    if (tplQ.isError) return <TemplateUnavailable error={tplQ.error} onRetry={() => void tplQ.refetch()} />;
    return (
      <p className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
        <Spinner /> {t("portal.templates.loadingTemplate", "Loading template…")}
      </p>
    );
  }

  const template = tplQ.data;
  return (
    <div className="space-y-4">
      <TemplateHeader template={template} />
      {template.kind === "report-card" ? <ReportCardDetail template={template} /> : <PsebDetail template={template} />}
    </div>
  );
}

function TemplateUnavailable({ error, onRetry }: { error?: unknown; onRetry?: () => void }) {
  const { t } = useTranslation();
  const status = axios.isAxiosError(error) ? error.response?.status : undefined;
  let message: string;
  if (error === undefined || status === 404) {
    message = t("portal.templates.notFound", "This template doesn't exist. It may have been deleted.");
  } else if (status === 403) {
    message = t("portal.templates.noAccess", "You don't have access to this template.");
  } else {
    message = `${t("portal.templates.loadError", "Couldn't load this template.")} ${apiError(error)}`;
  }
  const canRetry = !!onRetry && status !== 404 && status !== 403;
  return (
    <div className="space-y-3 p-6">
      <p className="text-muted-foreground">{message}</p>
      <div className="flex flex-wrap gap-2">
        <Button asChild variant="outline">
          <Link to="/templates">
            <ArrowLeft /> {t("portal.templates.allTemplates", "All templates")}
          </Link>
        </Button>
        {canRetry && (
          <Button variant="outline" onClick={onRetry}>
            {t("portal.common.tryAgain", "Try again")}
          </Button>
        )}
      </div>
    </div>
  );
}

function TemplateHeader({ template }: { template: PdfTemplate }) {
  const { t } = useTranslation();
  const { scopeLabel, layoutLabel } = useReportCardLabels();
  const isReportCard = template.kind === "report-card";
  const Icon = isReportCard ? FileText : ScrollText;

  const facts: { label: string; value: string }[] = [
    { label: t("portal.templates.session", "Session"), value: template.session },
  ];
  if (isReportCard || template.term) {
    facts.push({ label: t("portal.templates.term", "Term"), value: template.term || "—" });
  }
  if (isReportCard) {
    facts.push({ label: t("portal.templates.scope", "Scope"), value: scopeLabel(templateScope(template)) });
    facts.push({ label: t("portal.templates.layout", "Layout"), value: layoutLabel(template.layout) });
  }
  facts.push({ label: t("portal.templates.version", "Version"), value: `v${template.version}` });

  return (
    <div className="space-y-2">
      <Button asChild variant="ghost" size="sm" className="-ml-3">
        <Link to="/templates">
          <ArrowLeft /> {t("portal.templates.allTemplates", "All templates")}
        </Link>
      </Button>
      <h1 className="flex flex-wrap items-center gap-2 font-display text-heading-lg text-deep-indigo">
        <Icon className="h-6 w-6 shrink-0 text-khalsa-blue" aria-hidden />
        <span>
          {isReportCard
            ? t("portal.templates.kindReportCard", "Report card")
            : t("portal.templates.kindPseb", "PSEB admit card")}
        </span>
        <span className={cn(badgeVariants({ variant: "info" }), "font-body text-sm")}>{template.class_name}</span>
      </h1>
      <dl className="flex flex-wrap gap-x-6 gap-y-1 text-sm">
        {facts.map((f) => (
          <div key={f.label} className="flex items-baseline gap-1.5">
            <dt className="text-muted-foreground">{f.label}</dt>
            <dd className="font-medium text-foreground">{f.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}

// ── Report cards ─────────────────────────────────────────────────────────

function ReportCardDetail({ template }: { template: PdfTemplate }) {
  const { isAdmin } = useAuth();
  const [settingsDirty, setSettingsDirty] = useState(false);
  return (
    <>
      {template.scope == null && <MissingScopeNotice template={template} />}
      {isAdmin && (
        <ReportCardSettings
          // Not keyed on the version: setting the scope bumps it, and that mustn't drop what is typed here.
          key={template.id}
          template={template}
          onDirtyChange={setSettingsDirty}
        />
      )}
      {isAdmin && <PreviewCard template={template} settingsDirty={settingsDirty} />}
      <ReportCardRoster template={template} />
    </>
  );
}

/**
 * Templates made before scopes existed. When the term label says which results to
 * print ("Term I" is Term 1), the server already resolves, renders and previews the
 * cards with that scope, and an admin just confirms it to store it; otherwise the
 * cards can't be generated until an admin picks one. Either way it is set once (PATCH {scope}).
 */
function MissingScopeNotice({ template }: { template: PdfTemplate }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { isAdmin } = useAuth();
  const { scopeLabel } = useReportCardLabels();
  const selectId = useId();
  // What the cards print now, as the server reads it (the roster below shares this request).
  const rosterQ = useQuery(templateRosterQuery(template.id));
  const derived = rosterQ.data?.scope ?? scopeFromTerm(template.term);
  const [picked, setPicked] = useState<ResultScope | "">("");
  const scope = picked || derived || "";

  const save = useMutation({
    mutationFn: (next: ResultScope) =>
      api.patch<PdfTemplate>(`/pdf/templates/${template.id}`, { scope: next }).then((r) => r.data),
    onSuccess: (updated) => {
      qc.setQueryData(["pdf-template", template.id], updated);
      invalidateTemplate(qc, template.id);
      toast(t("portal.templates.scopeSaved", "Scope set to {{scope}}.", { scope: scopeLabel(updated.scope) }), "success");
    },
    onError: (e) => {
      toast(apiError(e), "error");
      // 409: it was set meanwhile, so show what it is now.
      if (axios.isAxiosError(e) && e.response?.status === 409) invalidateTemplate(qc, template.id);
    },
  });

  const confirmAndSave = () => {
    if (!scope) return;
    // Pinning another scope than the one the cards print changes what they print.
    const message =
      derived && scope !== derived
        ? t(
            "portal.templates.setScopeMismatchConfirm",
            "This template's cards print {{current}} results now. Set its scope to {{scope}} instead? It can't be changed afterwards.",
            { current: scopeLabel(derived), scope: scopeLabel(scope) },
          )
        : t("portal.templates.setScopeConfirm", "Set this template's scope to {{scope}}? It can't be changed afterwards.", {
            scope: scopeLabel(scope),
          });
    if (window.confirm(message)) save.mutate(scope);
  };

  // The cards already work from the term label, and only an admin can store the scope.
  if (derived && !isAdmin) return null;

  return (
    <div
      className={cn(
        "space-y-3 rounded-lg border p-4 text-sm",
        derived ? "border-info/30 bg-info/5" : "border-warning/40 bg-warning/10",
      )}
    >
      <div className="flex items-start gap-2">
        {derived ? (
          <Info className="mt-0.5 h-4 w-4 shrink-0 text-info" aria-hidden />
        ) : (
          <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-warning" aria-hidden />
        )}
        <div className="space-y-1">
          <p className="font-medium text-foreground">
            {derived
              ? t("portal.templates.scopeDerivedTitle", "Confirm which results this template prints")
              : t("portal.templates.scopeMissingTitle", "This template doesn't say which results it prints yet.")}
          </p>
          <p className="text-muted-foreground">
            {derived
              ? t(
                  "portal.templates.scopeDerivedAdmin",
                  "It was made before templates had a scope, so its cards print {{scope}} results, worked out from its term label. Confirm the scope to store it with the template. It can be set only once.",
                  { scope: scopeLabel(derived) },
                )
              : isAdmin
                ? t(
                    "portal.templates.scopeMissingAdmin",
                    "It was made before templates had a scope. Pick Term 1, Term 2 or Annual so its cards can be generated. The scope can be set only once.",
                  )
                : t(
                    "portal.templates.scopeMissingStaff",
                    "An admin has to pick Term 1, Term 2 or Annual before its cards can be generated.",
                  )}
          </p>
        </div>
      </div>
      {isAdmin && (
        <div className="flex flex-wrap items-end gap-2 sm:pl-6">
          <div className="space-y-1.5">
            <Label htmlFor={selectId}>{t("portal.templates.scope", "Scope")}</Label>
            <Select value={scope} onValueChange={(v) => setPicked(v as ResultScope)}>
              <SelectTrigger id={selectId} className="w-44 bg-background">
                <SelectValue placeholder={t("portal.templates.pickScope", "Pick a scope")} />
              </SelectTrigger>
              <SelectContent>
                {SCOPES.map((s) => (
                  <SelectItem key={s} value={s}>
                    {scopeLabel(s)}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
          <Button onClick={confirmAndSave} disabled={!scope || save.isPending}>
            {save.isPending ? <Spinner /> : <Save />}{" "}
            {derived && scope === derived
              ? t("portal.templates.confirmScope", "Confirm scope")
              : t("portal.templates.setScope", "Set scope")}
          </Button>
        </div>
      )}
    </div>
  );
}

/** What a card prints when its template doesn't say (the server's ReportCardTemplateData defaults). */
const SETTINGS_DEFAULTS: ReportCardTemplateData = {
  signatures: {},
  showAttendance: true,
  showRank: true,
  showPhoto: true,
  showGradingScale: true,
  includeDrafts: false,
  promotionRule: null,
  remarksDefault: null,
};

type ShowFlag = "showAttendance" | "showRank" | "showPhoto" | "showGradingScale";
const SHOW_FLAGS: ShowFlag[] = ["showAttendance", "showRank", "showPhoto", "showGradingScale"];
const SIGNATURES = ["classTeacher", "examIncharge", "principal"] as const;
type SettingsProblem = "passPct" | "conditionalMaxFails" | "englishRemarkMissing";

/** The settings form as its inputs hold it. */
interface SettingsForm extends Record<ShowFlag, boolean> {
  classTeacher: string;
  examIncharge: string;
  principal: string;
  layout: ReportLayout;
  includeDrafts: boolean;
  useDefaultRule: boolean;
  passPct: string;
  conditionalMaxFails: string;
  remarkEn: string;
  remarkPa: string;
}

function toSettingsForm(template: PdfTemplate, meta: Meta): SettingsForm {
  const d: ReportCardTemplateData = { ...SETTINGS_DEFAULTS, ...(template.data as Partial<ReportCardTemplateData>) };
  const sig = d.signatures ?? {};
  const rule = d.promotionRule ?? null;
  const flag = (v: unknown, fallback: boolean) => (typeof v === "boolean" ? v : fallback);
  return {
    classTeacher: sig.classTeacher ?? "",
    examIncharge: sig.examIncharge ?? "",
    principal: sig.principal ?? "",
    layout: template.layout === "components" ? "components" : "summary",
    showAttendance: flag(d.showAttendance, true),
    showRank: flag(d.showRank, true),
    showPhoto: flag(d.showPhoto, true),
    showGradingScale: flag(d.showGradingScale, true),
    includeDrafts: d.includeDrafts === true,
    useDefaultRule: rule == null,
    passPct: String(rule?.passPct ?? meta.pass_pct),
    conditionalMaxFails: String(rule?.conditionalMaxFails ?? meta.conditional_max_fails),
    remarkEn: d.remarksDefault?.en ?? "",
    remarkPa: d.remarksDefault?.pa ?? "",
  };
}

function settingsProblems(form: SettingsForm): SettingsProblem[] {
  const out: SettingsProblem[] = [];
  if (!form.useDefaultRule) {
    const pass = parseNumber(form.passPct);
    if (pass == null || pass < 0 || pass > 100) out.push("passPct");
    const fails = parseNumber(form.conditionalMaxFails);
    if (fails == null || !Number.isInteger(fails) || fails < 0 || fails > 20) out.push("conditionalMaxFails");
  }
  // The server refuses a Punjabi line without the English one (the card prints English first).
  if (!form.remarkEn.trim() && form.remarkPa.trim()) out.push("englishRemarkMissing");
  return out;
}

/**
 * template.data with the form's values. Keys this page doesn't edit are carried
 * over, so a setting the server adds later survives a save from here.
 */
function settingsData(form: SettingsForm, saved: Record<string, unknown>): Record<string, unknown> {
  const name = (s: string) => s.trim() || null;
  const savedSignatures =
    saved.signatures && typeof saved.signatures === "object" ? (saved.signatures as Record<string, unknown>) : {};
  const en = form.remarkEn.trim();
  const pa = form.remarkPa.trim();
  return {
    ...saved,
    signatures: {
      ...savedSignatures,
      classTeacher: name(form.classTeacher),
      examIncharge: name(form.examIncharge),
      principal: name(form.principal),
    },
    showAttendance: form.showAttendance,
    showRank: form.showRank,
    showPhoto: form.showPhoto,
    showGradingScale: form.showGradingScale,
    includeDrafts: form.includeDrafts,
    promotionRule: form.useDefaultRule
      ? null
      : { passPct: parseNumber(form.passPct) ?? 0, conditionalMaxFails: parseNumber(form.conditionalMaxFails) ?? 0 },
    remarksDefault: en || pa ? { en, pa: pa || null } : null,
  };
}

function ReportCardSettings({
  template, onDirtyChange,
}: {
  template: PdfTemplate;
  onDirtyChange: (dirty: boolean) => void;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { isSuperAdmin } = useAuth();
  const meta = useMeta();
  const { scopeLabel, layoutLabel, layoutHint } = useReportCardLabels();
  const uid = useId();
  const fieldId = (name: string) => `${uid}-${name}`;
  const printedScope = templateScope(template);

  const saved = template.data;
  const savedRule = (saved as Partial<ReportCardTemplateData>).promotionRule ?? null;
  const initial = useMemo(() => toSettingsForm(template, meta), [template, meta]);
  const [form, setForm] = useState<SettingsForm>(initial);
  const [ruleTouched, setRuleTouched] = useState(false);
  const set = <K extends keyof SettingsForm>(key: K, value: SettingsForm[K]) =>
    setForm((f) => ({ ...f, [key]: value }));

  // Before /meta loads, the default-rule numbers are fallbacks; follow the real ones in.
  useEffect(() => {
    if (savedRule || ruleTouched) return;
    setForm((f) => ({ ...f, passPct: String(meta.pass_pct), conditionalMaxFails: String(meta.conditional_max_fails) }));
  }, [meta.pass_pct, meta.conditional_max_fails, savedRule, ruleTouched]);

  const problems = settingsProblems(form);
  const data = settingsData(form, saved);
  const baseline = useMemo(() => JSON.stringify([initial.layout, settingsData(initial, saved)]), [initial, saved]);

  // When the saved settings change (this form's save, or another admin's arriving with a refetch),
  // the form starts again from them unless it holds edits matching neither the old nor the new
  // ones (typed while saving, or not saved yet). Setting the scope changes neither data nor layout.
  const [seed, setSeed] = useState({ baseline, saved });
  if (seed.baseline !== baseline) {
    const formAgainst = (s: Record<string, unknown>) => JSON.stringify([form.layout, settingsData(form, s)]);
    if (formAgainst(seed.saved) === seed.baseline || formAgainst(saved) === baseline) {
      setForm(initial);
      setRuleTouched(false);
    }
    setSeed({ baseline, saved });
  }
  const dirty = JSON.stringify([form.layout, data]) !== baseline;

  useEffect(() => {
    onDirtyChange(dirty);
  }, [dirty, onDirtyChange]);
  useEffect(() => () => onDirtyChange(false), [onDirtyChange]);
  // Reloading or a link to another page ("All templates", the menus) asks before dropping the form.
  useUnsavedChanges(dirty);

  const save = useMutation({
    mutationFn: (body: { data: Record<string, unknown>; layout: ReportLayout }) =>
      api.patch<PdfTemplate>(`/pdf/templates/${template.id}`, body).then((r) => r.data),
    onSuccess: (updated) => {
      // The new saved values start the form again (see the seed above).
      qc.setQueryData(["pdf-template", template.id], updated);
      invalidateTemplate(qc, template.id);
      toast(t("portal.templates.settingsSaved", "Card settings saved. Cards are re-rendered the next time they are generated."), "success");
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const discard = () => {
    setForm(initial);
    setRuleTouched(false);
  };

  const showLabels: Record<ShowFlag, string> = {
    showAttendance: t("portal.templates.showAttendance", "Show attendance"),
    showRank: t("portal.templates.showRank", "Show rank"),
    showPhoto: t("portal.templates.showPhoto", "Show photo"),
    showGradingScale: t("portal.templates.showGradingScale", "Show grading scale"),
  };
  const signatureLabels: Record<(typeof SIGNATURES)[number], string> = {
    classTeacher: t("portal.templates.classTeacher", "Class teacher"),
    examIncharge: t("portal.templates.examIncharge", "Examination in-charge"),
    principal: t("portal.templates.principal", "Principal"),
  };
  const problemText: Record<SettingsProblem, string> = {
    passPct: t("portal.templates.passPctInvalid", "Enter a pass mark from 0 to 100."),
    conditionalMaxFails: t("portal.templates.maxFailsInvalid", "Enter a whole number from 0 to 20."),
    englishRemarkMissing: t(
      "portal.reportCards.englishRemarkMissing",
      "Add the English remark too; the Punjabi line prints under it.",
    ),
  };
  const passInvalid = problems.includes("passPct");
  const failsInvalid = problems.includes("conditionalMaxFails");
  const englishMissing = problems.includes("englishRemarkMissing");
  const sectionTitle = "text-sm font-semibold text-deep-indigo";

  return (
    <Card>
      <CardHeader>
        <CardTitle role="heading" aria-level={2}>
          {t("portal.templates.settingsTitle", "Card settings")}
        </CardTitle>
        <CardDescription>
          {t("portal.templates.settingsHint", "Used on every {{scope}} report card of {{cls}} for {{session}}.", {
            scope: printedScope ? scopeLabel(printedScope) : template.term || "—",
            cls: template.class_name,
            session: template.session,
          })}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        <section className="space-y-3" aria-labelledby={fieldId("shows")}>
          <h3 id={fieldId("shows")} className={sectionTitle}>
            {t("portal.templates.whatPrints", "What the card shows")}
          </h3>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor={fieldId("layout")}>{t("portal.templates.layout", "Layout")}</Label>
              <Select value={form.layout} onValueChange={(v) => set("layout", v as ReportLayout)}>
                <SelectTrigger id={fieldId("layout")}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {LAYOUTS.map((l) => (
                    <SelectItem key={l} value={l}>
                      {layoutLabel(l)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">{layoutHint(form.layout, printedScope ?? "term1")}</p>
            </div>
            <div className="space-y-2.5">
              {SHOW_FLAGS.map((key) => (
                <label key={key} className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox checked={form[key]} onCheckedChange={(v) => set(key, v === true)} />
                  {showLabels[key]}
                </label>
              ))}
              {isSuperAdmin ? (
                <div className="space-y-0.5">
                  <label className="flex cursor-pointer items-center gap-2 text-sm">
                    <Checkbox checked={form.includeDrafts} onCheckedChange={(v) => set("includeDrafts", v === true)} />
                    {t("portal.templates.includeDrafts", "Include draft marks")}
                  </label>
                  <p className="pl-6 text-xs text-muted-foreground">
                    {t(
                      "portal.templates.includeDraftsHint",
                      "Prints marks whose batch is still a draft. Only a super-admin can change this.",
                    )}
                  </p>
                </div>
              ) : (
                form.includeDrafts && (
                  <p className="text-xs text-muted-foreground">
                    {t("portal.templates.includeDraftsOn", "A super-admin set these cards to include draft marks.")}
                  </p>
                )
              )}
            </div>
          </div>
        </section>

        <section className="space-y-3 border-t pt-5" aria-labelledby={fieldId("signatures")}>
          <div className="space-y-1">
            <h3 id={fieldId("signatures")} className={sectionTitle}>
              {t("portal.templates.signatures", "Signatures")}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t("portal.templates.signaturesHint", "Names printed under the signature lines. Leave a name blank for an empty line.")}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {SIGNATURES.map((key) => (
              <div key={key} className="space-y-1.5">
                <Label htmlFor={fieldId(key)}>{signatureLabels[key]}</Label>
                <Input id={fieldId(key)} value={form[key]} onChange={(e) => set(key, e.target.value)} />
              </div>
            ))}
          </div>
        </section>

        <section className="space-y-3 border-t pt-5" aria-labelledby={fieldId("rule")}>
          <h3 id={fieldId("rule")} className={sectionTitle}>
            {t("portal.templates.promotionRule", "Promotion rule")}
          </h3>
          <label className="flex cursor-pointer items-center gap-2 text-sm">
            <Checkbox checked={form.useDefaultRule} onCheckedChange={(v) => set("useDefaultRule", v === true)} />
            {t("portal.templates.useDefaultRule", "Use the school's default rule")}
          </label>
          {form.useDefaultRule ? (
            <p className="text-xs text-muted-foreground">
              {t(
                "portal.templates.defaultRuleIs",
                "School default: pass mark {{pct}}% in every academic subject; up to {{fails}} failed subjects means Conditional.",
                { pct: formatNumber(meta.pass_pct), fails: meta.conditional_max_fails },
              )}
            </p>
          ) : (
            <>
              <div className="flex flex-wrap gap-4">
                <div className="space-y-1.5">
                  <Label htmlFor={fieldId("passPct")}>{t("portal.templates.passPct", "Pass %")}</Label>
                  <NumberField
                    id={fieldId("passPct")}
                    className="w-28"
                    value={form.passPct}
                    min={0}
                    max={100}
                    invalid={passInvalid}
                    aria-invalid={passInvalid || undefined}
                    onChange={(v) => {
                      if (v.includes("-")) return;
                      setRuleTouched(true);
                      set("passPct", v);
                    }}
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor={fieldId("fails")}>
                    {t("portal.templates.conditionalMaxFails", "Max failed subjects for Conditional")}
                  </Label>
                  <NumberField
                    id={fieldId("fails")}
                    className="w-28"
                    value={form.conditionalMaxFails}
                    min={0}
                    max={20}
                    inputMode="numeric"
                    invalid={failsInvalid}
                    aria-invalid={failsInvalid || undefined}
                    onChange={(v) => {
                      // Whole subjects only.
                      if (v.includes("-") || v.includes(".")) return;
                      setRuleTouched(true);
                      set("conditionalMaxFails", v);
                    }}
                  />
                </div>
              </div>
              <p className="text-xs text-muted-foreground">
                {t(
                  "portal.templates.promotionRuleHint",
                  "Annual cards then print Promoted (no failed subject), Conditional (up to that many failed subjects) or Detained (more).",
                )}
              </p>
              {passInvalid && <p className="text-xs text-destructive">{problemText.passPct}</p>}
              {failsInvalid && <p className="text-xs text-destructive">{problemText.conditionalMaxFails}</p>}
            </>
          )}
        </section>

        <section className="space-y-3 border-t pt-5" aria-labelledby={fieldId("remark")}>
          <div className="space-y-1">
            <h3 id={fieldId("remark")} className={sectionTitle}>
              {t("portal.templates.remarksDefault", "Default remark")}
            </h3>
            <p className="text-xs text-muted-foreground">
              {t("portal.templates.remarksDefaultHint", "Printed only on the cards of students who have no remark of their own.")}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor={fieldId("remarkEn")}>{t("portal.templates.remarkEn", "Remark in English")}</Label>
              <Textarea
                id={fieldId("remarkEn")}
                rows={2}
                maxLength={REMARK_MAX}
                value={form.remarkEn}
                onChange={(e) => set("remarkEn", e.target.value)}
                aria-invalid={englishMissing || undefined}
                className={cn(englishMissing && "border-destructive focus-visible:ring-destructive")}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={fieldId("remarkPa")}>{t("portal.templates.remarkPa", "Remark in Punjabi")}</Label>
              <Textarea
                id={fieldId("remarkPa")}
                lang="pa"
                rows={2}
                maxLength={REMARK_MAX}
                className="font-gurmukhi"
                value={form.remarkPa}
                onChange={(e) => set("remarkPa", e.target.value)}
              />
            </div>
          </div>
          {englishMissing && <p className="text-xs text-destructive">{problemText.englishRemarkMissing}</p>}
        </section>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t pt-4">
          <p className="text-xs text-muted-foreground">
            {t("portal.templates.reRenderNote", "After saving, every card of this template is re-rendered the next time it is generated.")}
          </p>
          <div className="flex flex-wrap items-center gap-2">
            {dirty && !save.isPending && <Badge variant="warning">{t("portal.templates.unsaved", "Unsaved changes")}</Badge>}
            {dirty && (
              <Button variant="ghost" onClick={discard} disabled={save.isPending}>
                <Undo2 /> {t("portal.templates.discard", "Discard changes")}
              </Button>
            )}
            <Button
              onClick={() => save.mutate({ data, layout: form.layout })}
              disabled={!dirty || problems.length > 0 || save.isPending}
            >
              {save.isPending ? <Spinner /> : <Save />}{" "}
              {save.isPending ? t("portal.templates.saving", "Saving…") : t("portal.templates.saveSettings", "Save settings")}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/** Render one card with the saved settings, without the cache (admins). */
function PreviewCard({ template, settingsDirty }: { template: PdfTemplate; settingsDirty: boolean }) {
  const { t } = useTranslation();
  const { scopeLabel } = useReportCardLabels();
  const selectId = useId();
  // Same query as the roster below, so both share one request.
  const rosterQ = useQuery(templateRosterQuery(template.id));
  // An older template without a scope of its own previews the one the server reads from its term label.
  const scope = template.scope ?? rosterQ.data?.scope ?? null;
  const candidates = useMemo(() => (rosterQ.data?.students ?? []).filter((s) => s.has_marks), [rosterQ.data]);
  const [picked, setPicked] = useState("");
  const student = candidates.find((s) => String(s.id) === picked) ?? candidates[0];
  const [opening, setOpening] = useState(false);

  const preview = () => {
    if (!student) return;
    setOpening(true);
    // Straight from the click, so the new tab isn't stopped as a pop-up.
    void openReportCardPreview(template.id, student.id).finally(() => setOpening(false));
  };

  let body: ReactNode;
  if (rosterQ.isPending) {
    body = (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner /> {t("portal.templates.loadingStudents", "Loading students…")}
      </p>
    );
  } else if (!rosterQ.data) {
    body = (
      <p className="text-sm text-muted-foreground">
        {t("portal.templates.previewUnavailable", "The student list couldn't be loaded; see the report cards below.")}
      </p>
    );
  } else if (!candidates.length) {
    body = (
      <p className="text-sm text-muted-foreground">
        {t("portal.templates.previewNoMarks", "No student has marks for {{scope}} yet, so there is nothing to preview.", {
          scope: scopeLabel(scope),
        })}
      </p>
    );
  } else {
    body = (
      <div className="flex flex-wrap items-end gap-2">
        <div className="space-y-1.5">
          <Label htmlFor={selectId}>{t("portal.results.student", "Student")}</Label>
          <Select value={student ? String(student.id) : ""} onValueChange={setPicked}>
            <SelectTrigger id={selectId} className="w-72 max-w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {candidates.map((s) => (
                <SelectItem key={s.id} value={String(s.id)}>
                  {s.roll_no ? `${s.roll_no} · ${s.name}` : s.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <Button
          variant="outline"
          onClick={preview}
          disabled={!student || opening || scope == null || !!student.error}
        >
          {opening ? <Spinner /> : <Eye />} {t("portal.reportCards.preview", "Preview")}
        </Button>
      </div>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle role="heading" aria-level={2}>
          {t("portal.templates.previewTitle", "Preview a card")}
        </CardTitle>
        <CardDescription>
          {t("portal.templates.previewHint", "Shows one student's card with the saved settings in a new tab. Nothing is stored.")}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2">
        {body}
        {student?.error && <p className="text-xs text-destructive">{student.error}</p>}
        {settingsDirty && (
          <p className="text-xs text-warning">
            {t("portal.templates.previewUnsaved", "You have unsaved settings. The preview shows the saved ones, so save first to see your changes.")}
          </p>
        )}
      </CardContent>
    </Card>
  );
}

// ── PSEB admit cards ─────────────────────────────────────────────────────

type PsebData = Record<string, unknown>;
interface PsebDateSheetRow {
  subCode: string;
  subject: { en: string; pa: string };
  theoryDate: string;
  practical: string;
}
interface PsebInstruction {
  en: string;
  pa: string;
}
/** pdf_student_data.data for an admit card (backend: PsebAdmitCardStudentData). */
interface PsebStudentData {
  rollNo?: string;
  regNo?: string;
  category?: string;
  differentlyAbled?: string;
}
type PsebStudentKey = keyof PsebStudentData;
const PSEB_CATEGORIES = ["Regular", "Repeater", "Open"];

/** A field as the server stores it: trimmed, with the schema's defaults. */
function psebStored(key: PsebStudentKey, d: PsebStudentData | undefined): string {
  const v = (d?.[key] ?? (key === "differentlyAbled" ? "N.A." : "")).trim();
  return key === "category" ? v || "Regular" : v;
}

/**
 * Drop edited fields that equal the saved value. Run when the saved rows change, so a
 * save clears its own edits; anything typed while it was in flight, or not saved yet,
 * stays. Returns `prev` itself when nothing matches, so it never re-renders for nothing.
 */
function dropSavedPsebEdits(
  prev: ReadonlyMap<number, PsebStudentData>,
  saved: ReadonlyMap<number, PsebStudentData>,
): ReadonlyMap<number, PsebStudentData> {
  let changed = false;
  const next = new Map<number, PsebStudentData>();
  for (const [sid, edit] of prev) {
    const kept: PsebStudentData = {};
    for (const key of Object.keys(edit) as PsebStudentKey[]) {
      if (psebStored(key, edit) !== psebStored(key, saved.get(sid))) kept[key] = edit[key];
      else changed = true;
    }
    if (Object.keys(kept).length) next.set(sid, kept);
    else changed = true;
  }
  return changed ? next : prev;
}

function PsebDetail({ template }: { template: PdfTemplate }) {
  const { isAdmin } = useAuth();
  // Template settings and per-student data are admin writes; staff with the menu may view and generate.
  return (
    <>
      <PsebTemplateCard key={`${template.id}:${template.version}`} template={template} readOnly={!isAdmin} />
      <PsebStudentDataCard template={template} readOnly={!isAdmin} />
      <PsebRenderCard template={template} />
    </>
  );
}

function usePsebRoster(templateId: number) {
  return useQuery<PdfStudentRosterRow[]>({
    queryKey: ["pdf-roster", templateId],
    queryFn: () => api.get<PdfStudentRosterRow[]>(`/pdf/templates/${templateId}/students`).then((r) => r.data),
  });
}

function PsebTemplateCard({ template, readOnly }: { template: PdfTemplate; readOnly: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [data, setData] = useState<PsebData>(template.data);
  const dirty = JSON.stringify(data) !== JSON.stringify(template.data);
  useUnsavedChanges(dirty);

  const save = useMutation({
    mutationFn: (next: PsebData) =>
      api.patch<PdfTemplate>(`/pdf/templates/${template.id}`, { data: next }).then((r) => r.data),
    onSuccess: (updated) => {
      qc.setQueryData(["pdf-template", template.id], updated);
      invalidateTemplate(qc, template.id);
      toast(t("portal.templates.pseb.saved", "Admit card details saved. Cards are re-rendered the next time they are generated."), "success");
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle role="heading" aria-level={2}>
            {t("portal.templates.pseb.detailsTitle", "Admit card details")}
          </CardTitle>
          <CardDescription>
            {readOnly
              ? t("portal.templates.adminOnly", "Only an admin can change these.")
              : t("portal.templates.pseb.saveNote", "After saving, every admit card of this class is re-rendered the next time it is generated.")}
          </CardDescription>
        </div>
        {!readOnly && (
          <Button onClick={() => save.mutate(data)} disabled={!dirty || save.isPending}>
            {save.isPending ? <Spinner /> : <Save />}{" "}
            {save.isPending ? t("portal.templates.saving", "Saving…") : t("portal.common.save", "Save")}
          </Button>
        )}
      </CardHeader>
      <CardContent>
        <fieldset disabled={readOnly} className="min-w-0">
          <PsebTemplateForm data={data} setData={setData} />
        </fieldset>
      </CardContent>
    </Card>
  );
}

function TextField({
  label, value, onChange, punjabi = false, placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  punjabi?: boolean;
  placeholder?: string;
}) {
  const id = useId();
  return (
    <div className="space-y-1.5">
      <Label htmlFor={id}>{label}</Label>
      <Input
        id={id}
        value={value}
        placeholder={placeholder}
        lang={punjabi ? "pa" : undefined}
        className={cn(punjabi && "font-gurmukhi")}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

function PsebTemplateForm({ data, setData }: { data: PsebData; setData: (d: PsebData) => void }) {
  const { t } = useTranslation();
  const centre = (data.centre as Record<string, unknown> | undefined) ?? {};
  const centreName = (centre.name as { en?: string; pa?: string } | undefined) ?? {};
  const examTime = (data.examTime as { en?: string; pa?: string } | undefined) ?? {};
  const range = (data.practicalDateRange as { from?: string; to?: string } | null | undefined) ?? null;
  const sheet = (data.dateSheet as PsebDateSheetRow[] | undefined) ?? [];
  const instructions = (data.instructions as PsebInstruction[] | undefined) ?? [];

  const setCentre = (key: string, value: unknown) => setData({ ...data, centre: { ...centre, [key]: value } });
  const setCentreName = (lang: "en" | "pa", value: string) => setCentre("name", { ...centreName, [lang]: value });
  const setExamTime = (lang: "en" | "pa", value: string) => setData({ ...data, examTime: { ...examTime, [lang]: value } });
  const setRange = (key: "from" | "to", value: string) =>
    setData({ ...data, practicalDateRange: { from: "", to: "", ...(range ?? {}), [key]: value } });
  const setSheet = (next: PsebDateSheetRow[]) => setData({ ...data, dateSheet: next });
  const setSheetRow = (i: number, row: PsebDateSheetRow) => setSheet(sheet.map((r, j) => (j === i ? row : r)));
  const setInstructions = (next: PsebInstruction[]) => setData({ ...data, instructions: next });
  const setInstruction = (i: number, row: PsebInstruction) =>
    setInstructions(instructions.map((r, j) => (j === i ? row : r)));

  const str = (v: unknown) => (typeof v === "string" ? v : "");
  const removeLabel = t("portal.templates.pseb.removeRow", "Remove row");
  const codeLabel = t("portal.templates.pseb.code", "Code");
  const subjectEnLabel = t("portal.templates.pseb.subjectEn", "Subject (English)");
  const subjectPaLabel = t("portal.templates.pseb.subjectPa", "Subject (Punjabi)");
  const theoryLabel = t("portal.templates.pseb.theoryDate", "Theory (DD-MM-YYYY)");
  const practicalLabel = t("portal.templates.pseb.practical", "Practical");

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          label={t("portal.templates.pseb.schoolCode", "School code")}
          value={str(data.schoolCode)}
          onChange={(v) => setData({ ...data, schoolCode: v })}
        />
        <TextField
          label={t("portal.templates.pseb.examName", "Exam name")}
          value={str(data.examName)}
          placeholder={t("portal.templates.pseb.examNamePlaceholder", "PSEB Class X — Annual 2026")}
          onChange={(v) => setData({ ...data, examName: v })}
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <TextField label={t("portal.templates.pseb.centreCode", "Centre code")} value={str(centre.code)} onChange={(v) => setCentre("code", v)} />
        <TextField
          label={t("portal.templates.pseb.centreSchoolCode", "Centre school code")}
          value={str(centre.schoolCode)}
          onChange={(v) => setCentre("schoolCode", v)}
        />
        <TextField label={t("portal.templates.pseb.district", "District")} value={str(centre.district)} onChange={(v) => setCentre("district", v)} />
        <TextField label={t("portal.templates.pseb.set", "Set")} value={str(centre.set)} onChange={(v) => setCentre("set", v)} />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          label={t("portal.templates.pseb.centreNameEn", "Centre name (English)")}
          value={centreName.en ?? ""}
          onChange={(v) => setCentreName("en", v)}
        />
        <TextField
          label={t("portal.templates.pseb.centreNamePa", "Centre name (Punjabi)")}
          value={centreName.pa ?? ""}
          onChange={(v) => setCentreName("pa", v)}
          punjabi
        />
      </div>

      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          label={t("portal.templates.pseb.examTimeEn", "Exam time (English)")}
          value={examTime.en ?? ""}
          onChange={(v) => setExamTime("en", v)}
        />
        <TextField
          label={t("portal.templates.pseb.examTimePa", "Exam time (Punjabi)")}
          value={examTime.pa ?? ""}
          onChange={(v) => setExamTime("pa", v)}
          punjabi
        />
      </div>
      <div className="grid gap-3 sm:grid-cols-2">
        <TextField
          label={t("portal.templates.pseb.practicalFrom", "Practical from (DD-MM-YYYY)")}
          value={range?.from ?? ""}
          onChange={(v) => setRange("from", v)}
        />
        <TextField
          label={t("portal.templates.pseb.practicalTo", "Practical to (DD-MM-YYYY)")}
          value={range?.to ?? ""}
          onChange={(v) => setRange("to", v)}
        />
      </div>

      <div className="space-y-2 border-t pt-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-deep-indigo">{t("portal.templates.pseb.dateSheet", "Date sheet")}</h3>
          <Button
            type="button"
            size="sm"
            variant="outline"
            onClick={() => setSheet([...sheet, { subCode: "", subject: { en: "", pa: "" }, theoryDate: "", practical: "No" }])}
          >
            <Plus /> {t("portal.templates.pseb.addRow", "Add row")}
          </Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-24">{codeLabel}</TableHead>
              <TableHead>{subjectEnLabel}</TableHead>
              <TableHead>{subjectPaLabel}</TableHead>
              <TableHead className="w-36">{theoryLabel}</TableHead>
              <TableHead className="w-28">{practicalLabel}</TableHead>
              <TableHead className="w-12">
                <span className="sr-only">{removeLabel}</span>
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sheet.map((r, i) => (
              <TableRow key={i}>
                <TableCell>
                  <Input className="h-8" aria-label={codeLabel} value={r.subCode} onChange={(e) => setSheetRow(i, { ...r, subCode: e.target.value })} />
                </TableCell>
                <TableCell>
                  <Input
                    className="h-8 min-w-[10rem]"
                    aria-label={subjectEnLabel}
                    value={r.subject.en}
                    onChange={(e) => setSheetRow(i, { ...r, subject: { ...r.subject, en: e.target.value } })}
                  />
                </TableCell>
                <TableCell>
                  <Input
                    lang="pa"
                    className="h-8 min-w-[10rem] font-gurmukhi"
                    aria-label={subjectPaLabel}
                    value={r.subject.pa}
                    onChange={(e) => setSheetRow(i, { ...r, subject: { ...r.subject, pa: e.target.value } })}
                  />
                </TableCell>
                <TableCell>
                  <Input className="h-8" aria-label={theoryLabel} value={r.theoryDate} onChange={(e) => setSheetRow(i, { ...r, theoryDate: e.target.value })} />
                </TableCell>
                <TableCell>
                  <Select value={r.practical} onValueChange={(v) => setSheetRow(i, { ...r, practical: v })}>
                    <SelectTrigger className="h-8" aria-label={practicalLabel}>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Yes">{t("portal.common.yes", "Yes")}</SelectItem>
                      <SelectItem value="No">{t("portal.common.no", "No")}</SelectItem>
                    </SelectContent>
                  </Select>
                </TableCell>
                <TableCell>
                  <Button
                    type="button"
                    size="icon"
                    variant="ghost"
                    className="h-8 w-8 text-destructive hover:text-destructive"
                    aria-label={removeLabel}
                    onClick={() => setSheet(sheet.filter((_, j) => j !== i))}
                  >
                    <Trash2 />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-2 border-t pt-4">
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-semibold text-deep-indigo">{t("portal.templates.pseb.instructions", "Instructions")}</h3>
          <Button type="button" size="sm" variant="outline" onClick={() => setInstructions([...instructions, { en: "", pa: "" }])}>
            <Plus /> {t("portal.common.add", "Add")}
          </Button>
        </div>
        {instructions.map((ins, i) => (
          <div key={i} className="flex items-start gap-2">
            <Textarea
              rows={1}
              className="flex-1"
              value={ins.en}
              placeholder={t("portal.templates.pseb.instructionEn", "Instruction in English")}
              aria-label={t("portal.templates.pseb.instructionEn", "Instruction in English")}
              onChange={(e) => setInstruction(i, { ...ins, en: e.target.value })}
            />
            <Textarea
              rows={1}
              lang="pa"
              className="flex-1 font-gurmukhi"
              value={ins.pa}
              placeholder={t("portal.templates.pseb.instructionPa", "Instruction in Punjabi")}
              aria-label={t("portal.templates.pseb.instructionPa", "Instruction in Punjabi")}
              onChange={(e) => setInstruction(i, { ...ins, pa: e.target.value })}
            />
            <Button
              type="button"
              size="icon"
              variant="ghost"
              className="text-destructive hover:text-destructive"
              aria-label={removeLabel}
              onClick={() => setInstructions(instructions.filter((_, j) => j !== i))}
            >
              <Trash2 />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

function PsebStudentDataCard({ template, readOnly }: { template: PdfTemplate; readOnly: boolean }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const rosterQ = usePsebRoster(template.id);
  const dataQ = useQuery<PdfStudentDataRow[]>({
    queryKey: ["pdf-student-data", template.id],
    queryFn: () => api.get<PdfStudentDataRow[]>(`/pdf/templates/${template.id}/student-data`).then((r) => r.data),
  });

  const saved = useMemo(() => {
    const m = new Map<number, PsebStudentData>();
    for (const row of dataQ.data ?? []) m.set(row.student_id, row.data as PsebStudentData);
    return m;
  }, [dataQ.data]);
  // Only the fields changed here, laid over the saved row: a refetch (this card's save, or
  // another admin's) drops just the edits it now matches and keeps the rest.
  const [edits, setEdits] = useState<ReadonlyMap<number, PsebStudentData>>(() => new Map());
  useEffect(() => setEdits((prev) => dropSavedPsebEdits(prev, saved)), [saved]);

  const valueOf = (sid: number): PsebStudentData => ({ ...saved.get(sid), ...edits.get(sid) });
  const setField = (sid: number, key: PsebStudentKey, value: string) =>
    setEdits((prev) => {
      const next = new Map(prev);
      next.set(sid, { ...prev.get(sid), [key]: value });
      return next;
    });
  // The server needs both numbers on every saved row.
  const incomplete = (d: PsebStudentData) => !d.rollNo?.trim() || !d.regNo?.trim();
  const blocked = [...edits.keys()].some((sid) => incomplete(valueOf(sid)));
  useUnsavedChanges(edits.size > 0);

  const studentDataKey = ["pdf-student-data", template.id];
  const save = useMutation({
    mutationFn: (entries: { student_id: number; data: PsebStudentData }[]) =>
      api.put<PdfStudentDataRow[]>(`/pdf/templates/${template.id}/student-data`, { entries }).then((r) => r.data),
    onSuccess: (rows, entries) => {
      // The saved rows clear the matching edits in the same render (dropSavedPsebEdits).
      qc.setQueryData<PdfStudentDataRow[]>(studentDataKey, (old) => {
        const byId = new Map((old ?? []).map((r) => [r.student_id, r]));
        for (const r of rows) byId.set(r.student_id, r);
        return [...byId.values()];
      });
      toast(t("portal.templates.pseb.studentsSaved", "Saved details for {{count}} students", { count: entries.length }), "success");
      qc.invalidateQueries({ queryKey: studentDataKey });
      qc.invalidateQueries({ queryKey: ["pdf-roster", template.id] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });
  // Whole rows (saved values plus the edits), trimmed: a new row needs both numbers.
  const saveAll = () =>
    save.mutate(
      [...edits.keys()].map((student_id) => ({
        student_id,
        data: Object.fromEntries(
          Object.entries(valueOf(student_id)).map(([k, v]) => [k, typeof v === "string" ? v.trim() : v]),
        ),
      })),
    );

  const categoryLabel: Record<string, string> = {
    Regular: t("portal.templates.pseb.categoryRegular", "Regular"),
    Repeater: t("portal.templates.pseb.categoryRepeater", "Repeater"),
    Open: t("portal.templates.pseb.categoryOpen", "Open"),
  };
  const rollLabel = t("portal.templates.pseb.rollNo", "PSEB roll no.");
  const regLabel = t("portal.templates.pseb.regNo", "Registration no.");
  const categoryHead = t("portal.templates.pseb.category", "Category");
  const abledLabel = t("portal.templates.pseb.differentlyAbled", "Differently abled");
  const students = rosterQ.data ?? [];

  let body: ReactNode;
  if (rosterQ.isPending) {
    body = (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner /> {t("portal.common.loading", "Loading…")}
      </p>
    );
  } else if (!rosterQ.data) {
    body = (
      <p role="alert" className="text-sm text-destructive">
        {t("portal.templates.studentsLoadError", "Couldn't load the students.")} {apiError(rosterQ.error)}
      </p>
    );
  } else if (!students.length) {
    body = (
      <p className="text-sm text-muted-foreground">
        {t("portal.templates.noStudents", "No active students in {{cls}}.", { cls: template.class_name })}
      </p>
    );
  } else {
    body = (
      <fieldset disabled={readOnly || !dataQ.data} className="min-w-0">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-10">#</TableHead>
              <TableHead>{t("portal.results.student", "Student")}</TableHead>
              <TableHead>{rollLabel}</TableHead>
              <TableHead>{regLabel}</TableHead>
              <TableHead>{categoryHead}</TableHead>
              <TableHead>{abledLabel}</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {students.map((s, i) => {
              const d = valueOf(s.id);
              const edited = edits.has(s.id);
              const bad = edited && incomplete(d);
              const category = d.category || "Regular";
              const categories = PSEB_CATEGORIES.includes(category) ? PSEB_CATEGORIES : [...PSEB_CATEGORIES, category];
              return (
                <TableRow key={s.id} className={cn(edited && "bg-vasant-cream/40")}>
                  <TableCell className="tabular-nums text-muted-foreground">{i + 1}</TableCell>
                  <TableCell className="min-w-[10rem]">
                    <div className="font-medium">{s.name}</div>
                    {edited && (
                      <Badge variant="warning" className="mt-1">{t("portal.templates.unsaved", "Unsaved changes")}</Badge>
                    )}
                    {bad && (
                      <p className="mt-1 text-xs text-destructive">
                        {t("portal.templates.pseb.missingIds", "Fill in the roll no. and registration no.")}
                      </p>
                    )}
                  </TableCell>
                  <TableCell>
                    <Input
                      className={cn("h-8 w-32", bad && !d.rollNo?.trim() && "border-destructive")}
                      value={d.rollNo ?? ""}
                      aria-label={`${rollLabel} · ${s.name}`}
                      onChange={(e) => setField(s.id, "rollNo", e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <Input
                      className={cn("h-8 w-36", bad && !d.regNo?.trim() && "border-destructive")}
                      value={d.regNo ?? ""}
                      aria-label={`${regLabel} · ${s.name}`}
                      onChange={(e) => setField(s.id, "regNo", e.target.value)}
                    />
                  </TableCell>
                  <TableCell>
                    <Select value={category} onValueChange={(v) => setField(s.id, "category", v)}>
                      <SelectTrigger className="h-8 w-32" aria-label={`${categoryHead} · ${s.name}`}>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {categories.map((c) => (
                          <SelectItem key={c} value={c}>
                            {categoryLabel[c] ?? c}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </TableCell>
                  <TableCell>
                    <Input
                      className="h-8 w-28"
                      value={d.differentlyAbled ?? "N.A."}
                      aria-label={`${abledLabel} · ${s.name}`}
                      onChange={(e) => setField(s.id, "differentlyAbled", e.target.value)}
                    />
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </fieldset>
    );
  }

  return (
    <Card>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle role="heading" aria-level={2} className="flex flex-wrap items-center gap-2">
            {t("portal.templates.pseb.studentData", "Per-student details")}
            {edits.size > 0 && (
              <Badge variant="warning">{t("portal.templates.unsavedCount", "{{n}} unsaved", { n: edits.size })}</Badge>
            )}
          </CardTitle>
          <CardDescription>
            {readOnly
              ? t("portal.templates.adminOnly", "Only an admin can change these.")
              : t("portal.templates.pseb.requiredHint", "Each student needs a PSEB roll no. and registration no. before their details can be saved.")}
          </CardDescription>
        </div>
        {!readOnly && (
          <Button onClick={saveAll} disabled={!edits.size || blocked || save.isPending}>
            {save.isPending ? <Spinner /> : <Save />}{" "}
            {edits.size
              ? t("portal.templates.saveCount", "Save {{count}} changes", { count: edits.size })
              : t("portal.templates.saveChanges", "Save changes")}
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-3">
        {dataQ.isError && !dataQ.data && (
          <div
            role="alert"
            className="flex flex-wrap items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive"
          >
            <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
            <span>
              {t("portal.templates.pseb.dataLoadError", "Couldn't load the saved details, so editing is paused.")}{" "}
              {apiError(dataQ.error)}
            </span>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => void dataQ.refetch()}>
              {t("portal.common.tryAgain", "Try again")}
            </Button>
          </div>
        )}
        {body}
      </CardContent>
    </Card>
  );
}

function PsebRenderCard({ template }: { template: PdfTemplate }) {
  const { t } = useTranslation();
  // Force re-render is admin-only (the server ignores it from staff), like the report-card roster.
  const { isAdmin } = useAuth();
  const qc = useQueryClient();
  const rosterQ = usePsebRoster(template.id);
  const students = useMemo(() => rosterQ.data ?? [], [rosterQ.data]);

  const [selected, setSelected] = useState<ReadonlySet<number>>(() => new Set());
  const [force, setForce] = useState(false);
  const [results, setResults] = useState<ReadonlyMap<number, PdfRenderResultRow>>(() => new Map());
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(null);

  const selectedIds = students.filter((s) => selected.has(s.id)).map((s) => s.id);
  const allSelected = students.length > 0 && selectedIds.length === students.length;
  const toggleAll = () => setSelected(allSelected ? new Set() : new Set(students.map((s) => s.id)));
  const toggleOne = (id: number) =>
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });

  // The synchronous render takes RENDER_CHUNK students per request, so bigger selections go in turns.
  const render = useMutation({
    mutationFn: async ({ ids, force: forceRender }: { ids: number[]; force: boolean }) => {
      const all: PdfRenderResultRow[] = [];
      setResults(new Map());
      setProgress({ done: 0, total: ids.length });
      for (let i = 0; i < ids.length; i += RENDER_CHUNK) {
        const chunk = ids.slice(i, i + RENDER_CHUNK);
        const { data } = await api.post<{ results: PdfRenderResultRow[] }>(
          `/pdf/templates/${template.id}/render`,
          { student_ids: chunk, force: forceRender },
          { timeout: RENDER_TIMEOUT_MS },
        );
        all.push(...data.results);
        setResults((prev) => {
          const next = new Map(prev);
          for (const r of data.results) next.set(r.student_id, r);
          return next;
        });
        setProgress({ done: Math.min(i + chunk.length, ids.length), total: ids.length });
      }
      return all;
    },
    onSuccess: (rows) => {
      const ok = rows.filter((r) => r.status !== "error").length;
      toast(
        t("portal.templates.pseb.readyToast", "{{ok}} of {{total}} admit cards ready", { ok, total: rows.length }),
        ok === rows.length ? "success" : "warning",
      );
    },
    onError: (e) => toast(apiError(e), "error"),
    onSettled: () => {
      setProgress(null);
      qc.invalidateQueries({ queryKey: ["pdf-roster", template.id] });
    },
  });

  const statusOf = (s: PdfStudentRosterRow): PdfRenderResultRow["status"] | null =>
    results.get(s.id)?.status ?? (s.cached_pdf_id ? "cached" : null);
  // The current card first; else an outdated one, still useful until it is generated again.
  const pdfIdOf = (s: PdfStudentRosterRow): number | null =>
    results.get(s.id)?.pdf_id ?? s.cached_pdf_id ?? s.stale_pdf_id ?? null;
  const downloadLabel = t("portal.common.download", "Download");
  const outdatedLabel = t("portal.reportCards.downloadOutdated", "Download the outdated card");

  let buttonText: string;
  if (progress) {
    buttonText = t("portal.templates.pseb.progress", "Generating… {{done}} of {{total}} done", progress);
  } else if (selectedIds.length) {
    buttonText = t("portal.templates.pseb.generateCount", "Generate ({{n}})", { n: selectedIds.length });
  } else {
    buttonText = t("portal.templates.pseb.generate", "Generate");
  }

  return (
    <Card>
      <CardHeader className="space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle role="heading" aria-level={2}>
            {t("portal.templates.pseb.generateTitle", "Generate admit cards")}
          </CardTitle>
          <div className="flex flex-wrap items-center gap-3">
            {isAdmin && (
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <Checkbox checked={force} onCheckedChange={(v) => setForce(v === true)} />
                {t("portal.templates.force", "Force re-render (ignore saved PDFs)")}
              </label>
            )}
            <Button
              onClick={() => render.mutate({ ids: selectedIds, force: isAdmin && force })}
              disabled={!selectedIds.length || render.isPending}
            >
              {render.isPending ? <Spinner /> : <RefreshCw />} {buttonText}
            </Button>
          </div>
        </div>
        {selectedIds.length > RENDER_CHUNK && (
          <CardDescription>
            {t("portal.templates.pseb.chunkHint", "Cards are generated {{n}} at a time; keep this page open until it finishes.", {
              n: RENDER_CHUNK,
            })}
          </CardDescription>
        )}
      </CardHeader>
      <CardContent>
        {rosterQ.isPending ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> {t("portal.common.loading", "Loading…")}
          </p>
        ) : !students.length ? (
          <p className="text-sm text-muted-foreground">
            {rosterQ.isError
              ? `${t("portal.templates.studentsLoadError", "Couldn't load the students.")} ${apiError(rosterQ.error)}`
              : t("portal.templates.noStudents", "No active students in {{cls}}.", { cls: template.class_name })}
          </p>
        ) : (
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={allSelected}
                    onCheckedChange={toggleAll}
                    aria-label={t("portal.reportCards.selectAll", "Select all students")}
                  />
                </TableHead>
                <TableHead>{t("portal.results.student", "Student")}</TableHead>
                <TableHead>{t("portal.templates.pseb.dataColumn", "Details")}</TableHead>
                <TableHead>{t("portal.templates.pseb.status", "Status")}</TableHead>
                <TableHead className="text-right">{downloadLabel}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {students.map((s) => {
                const result = results.get(s.id);
                const status = statusOf(s);
                const pdfId = pdfIdOf(s);
                const outdated = pdfId != null && !result?.pdf_id && s.cached_pdf_id == null;
                // This run's answer, else why the roster says the card can't be made now.
                const problem = result ? result.error : s.error;
                const download = outdated ? outdatedLabel : downloadLabel;
                return (
                  <TableRow key={s.id} data-state={selected.has(s.id) ? "selected" : undefined}>
                    <TableCell>
                      <Checkbox
                        checked={selected.has(s.id)}
                        onCheckedChange={() => toggleOne(s.id)}
                        aria-label={t("portal.reportCards.selectStudent", "Select {{name}}", { name: s.name })}
                      />
                    </TableCell>
                    <TableCell>
                      <div className="font-medium">{s.name}</div>
                      {s.missing_dob && (
                        <Badge
                          variant="warning"
                          className="mt-1"
                          title={t(
                            "portal.templates.pseb.missingDobHint",
                            "No date of birth on the student's record: the admit card can't be generated until it is added.",
                          )}
                        >
                          {t("portal.reportCards.missingDob", "DOB missing")}
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {s.has_data ? (
                        <Badge variant="success">{t("portal.templates.pseb.filled", "Filled")}</Badge>
                      ) : (
                        <Badge variant="warning">{t("portal.templates.pseb.missing", "Missing")}</Badge>
                      )}
                    </TableCell>
                    <TableCell>
                      {status === "rendered" && <Badge variant="success">{t("portal.templates.pseb.rendered", "Generated")}</Badge>}
                      {status === "cached" && <Badge variant="info">{t("portal.templates.pseb.cached", "Ready")}</Badge>}
                      {status === "error" && <Badge variant="destructive">{t("portal.templates.pseb.failed", "Failed")}</Badge>}
                      {status == null &&
                        (s.error ? (
                          <Badge variant="destructive">{t("portal.reportCards.cantGenerate", "Can't generate")}</Badge>
                        ) : s.stale_pdf_id != null ? (
                          <Badge variant="warning">{t("portal.reportCards.stale", "Needs update")}</Badge>
                        ) : (
                          <span className="text-xs text-muted-foreground">—</span>
                        ))}
                      {problem && <div className="mt-1 max-w-md text-xs text-destructive">{problem}</div>}
                    </TableCell>
                    <TableCell className="text-right">
                      {pdfId ? (
                        <Button
                          size="icon"
                          variant="outline"
                          className="h-8 w-8"
                          title={download}
                          aria-label={`${download} · ${s.name}`}
                          onClick={() => downloadCachedPdf(pdfId, pdfFilename(template.kind, template.class_name, s))}
                        >
                          <FileDown />
                        </Button>
                      ) : (
                        <span className="text-xs text-muted-foreground">—</span>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        )}
      </CardContent>
    </Card>
  );
}
