import { useId, useMemo, useState, type ReactNode } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { FileCheck2, FileText, Plus, ScrollText, Trash2, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/toaster";
import { SessionSelect } from "@/components/SessionSelect";
import { templateScope, useReportCardLabels } from "@/components/report-cards/labels";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useCurrentSessionName, useSessions } from "@/lib/session";
import { CLASSES } from "@/lib/utils";
import type { PdfTemplate, PdfTemplateBulkCreateResult, PdfTemplateKind, ReportLayout, ResultScope } from "@/types/api";

/** Select sentinel: a Radix item value can never be "". */
const ALL_SESSIONS = "__all__";
const SCOPES: ResultScope[] = ["term1", "term2", "annual"];
const LAYOUTS: ReportLayout[] = ["summary", "components"];
/** The label the server stores when none is typed (SCOPE_LABELS in app/services/report_cards.py). */
const DEFAULT_TERM_LABEL: Record<ResultScope, string> = { term1: "Term I", term2: "Term II", annual: "Annual" };
const TERM_LABEL_MAX = 32; // pdf_templates.term is VARCHAR(32)
const KIND_ORDER: Record<PdfTemplateKind, number> = { "report-card": 0, "pseb-admit-card": 1 };
const SCOPE_ORDER: Record<ResultScope, number> = { term1: 0, term2: 1, annual: 2 };

/** A new PSEB admit-card template starts from this (its schema needs a centre, exam time and one date-sheet row). */
const PSEB_SEED = {
  schoolCode: "0098351",
  centre: { code: "", schoolCode: "", district: "", set: "", name: { en: "", pa: "" } },
  examTime: { en: "", pa: "" },
  dateSheet: [{ subCode: "", subject: { en: "", pa: "" }, theoryDate: "", practical: "No" }],
  instructions: [],
};

interface CreateBody {
  kind: PdfTemplateKind;
  class_name: string;
  session: string;
  scope?: ResultScope;
  layout?: ReportLayout;
  term?: string | null;
  data: object;
}

interface BulkCreateBody {
  kind: "report-card";
  session: string;
  scope: ResultScope;
  layout: ReportLayout;
  term?: string;
  class_names: string[] | null; // null = every class
  data: object;
}

/** "18 Oct 2026, 02:05 pm" */
function formatStamp(iso: string): string {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("en-IN", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" });
}

function classIndex(cls: string): number {
  const i = CLASSES.indexOf(cls);
  return i < 0 ? CLASSES.length : i;
}

/** Newest session first, then report cards before admit cards, then school class order, then term. */
function compareTemplates(a: PdfTemplate, b: PdfTemplate): number {
  const scopeA = a.kind === "report-card" ? templateScope(a) : null;
  const scopeB = b.kind === "report-card" ? templateScope(b) : null;
  return (
    b.session.localeCompare(a.session) ||
    (KIND_ORDER[a.kind] ?? 9) - (KIND_ORDER[b.kind] ?? 9) ||
    classIndex(a.class_name) - classIndex(b.class_name) ||
    (scopeA ? SCOPE_ORDER[scopeA] : 9) - (scopeB ? SCOPE_ORDER[scopeB] : 9) ||
    (a.term ?? "").localeCompare(b.term ?? "") ||
    a.id - b.id
  );
}

function useKindLabel() {
  const { t } = useTranslation();
  return (kind: PdfTemplateKind): string =>
    kind === "report-card"
      ? t("portal.templates.kindReportCard", "Report card")
      : t("portal.templates.kindPseb", "PSEB admit card");
}

export default function Templates() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { isAdmin } = useAuth();
  const { scopeLabel, layoutLabel } = useReportCardLabels();
  const kindLabel = useKindLabel();
  const sessionsQ = useSessions();
  const filterId = useId();
  const [newOpen, setNewOpen] = useState(false);
  const [sessionFilter, setSessionFilter] = useState(ALL_SESSIONS);

  const listQ = useQuery<PdfTemplate[]>({
    queryKey: ["pdf-templates"],
    queryFn: () => api.get<PdfTemplate[]>("/pdf/templates").then((r) => r.data),
  });
  const templates = useMemo(() => listQ.data ?? [], [listQ.data]);

  // Configured sessions, plus any a template still points at.
  const sessionOptions = useMemo(() => {
    const names = (sessionsQ.data ?? []).map((s) => s.session);
    for (const row of templates) if (!names.includes(row.session)) names.push(row.session);
    return [...names].sort((a, b) => b.localeCompare(a));
  }, [sessionsQ.data, templates]);
  const currentSession = sessionsQ.data?.find((s) => s.is_current)?.session;

  const rows = useMemo(
    () => templates.filter((r) => sessionFilter === ALL_SESSIONS || r.session === sessionFilter).sort(compareTemplates),
    [templates, sessionFilter],
  );

  const del = useMutation({
    mutationFn: (id: number) => api.delete(`/pdf/templates/${id}`),
    onSuccess: (_res, id) => {
      qc.removeQueries({ queryKey: ["pdf-template", id] });
      qc.removeQueries({ queryKey: ["pdf-roster", id] });
      qc.invalidateQueries({ queryKey: ["pdf-templates"] });
      qc.invalidateQueries({ queryKey: ["pdf-template-resolve"] });
      // The results table grades with the class's report-card rule, which may have been this one's.
      qc.invalidateQueries({ queryKey: ["results"] });
      toast(t("portal.templates.deleted", "Template deleted"), "warning");
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const describe = (row: PdfTemplate) =>
    [kindLabel(row.kind), row.class_name, row.session, row.term].filter(Boolean).join(" · ");
  const confirmDelete = (row: PdfTemplate) => {
    const ok = window.confirm(
      t(
        "portal.templates.deleteConfirm",
        "Delete “{{name}}”? Its generated PDFs are deleted too. Remarks and other per-student entries stay saved.",
        { name: describe(row) },
      ),
    );
    if (ok) del.mutate(row.id);
  };

  let body: ReactNode;
  if (listQ.isPending) {
    body = (
      <p className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner /> {t("portal.common.loading", "Loading…")}
      </p>
    );
  } else if (listQ.isError && !listQ.data) {
    body = (
      <div role="alert" className="flex flex-wrap items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
        <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
        <span>
          {t("portal.templates.listError", "Couldn't load the templates.")} {apiError(listQ.error)}
        </span>
        <Button variant="outline" size="sm" className="ml-auto" onClick={() => void listQ.refetch()}>
          {t("portal.common.tryAgain", "Try again")}
        </Button>
      </div>
    );
  } else if (!templates.length) {
    body = (
      <p className="text-sm text-muted-foreground">
        {isAdmin
          ? t("portal.templates.emptyAdmin", "No templates yet. Use “New template” to set up report cards for every class in one go.")
          : t("portal.templates.emptyStaff", "No templates for your classes yet.")}
      </p>
    );
  } else if (!rows.length) {
    body = (
      <div className="flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
        <span>{t("portal.templates.emptySession", "No templates for {{session}}.", { session: sessionFilter })}</span>
        <Button variant="outline" size="sm" onClick={() => setSessionFilter(ALL_SESSIONS)}>
          {t("portal.templates.showAllSessions", "Show all sessions")}
        </Button>
      </div>
    );
  } else {
    body = (
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("portal.templates.kind", "Kind")}</TableHead>
            <TableHead>{t("portal.templates.class", "Class")}</TableHead>
            <TableHead>{t("portal.templates.session", "Session")}</TableHead>
            <TableHead>{t("portal.templates.term", "Term")}</TableHead>
            <TableHead>{t("portal.templates.layout", "Layout")}</TableHead>
            <TableHead>{t("portal.templates.version", "Version")}</TableHead>
            <TableHead>{t("portal.templates.lastUpdated", "Last updated")}</TableHead>
            <TableHead className="text-right">{t("portal.common.actions", "Actions")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.map((row) => {
            const isReportCard = row.kind === "report-card";
            const Icon = isReportCard ? FileText : ScrollText;
            // An older template without a scope of its own prints the one its term label stands for.
            const scope = isReportCard ? templateScope(row) : null;
            return (
              <TableRow key={row.id}>
                <TableCell className="whitespace-nowrap">
                  <span className="inline-flex items-center gap-2">
                    <Icon className="h-4 w-4 text-khalsa-blue" aria-hidden />
                    {kindLabel(row.kind)}
                  </span>
                </TableCell>
                <TableCell>
                  <Badge variant="info">{row.class_name}</Badge>
                </TableCell>
                <TableCell className="whitespace-nowrap">{row.session}</TableCell>
                <TableCell className="whitespace-nowrap">
                  <div>{row.term || "—"}</div>
                  {isReportCard &&
                    (scope ? (
                      <div className="text-xs text-muted-foreground">
                        {row.scope
                          ? t("portal.templates.scopeIs", "Scope: {{scope}}", { scope: scopeLabel(scope) })
                          : t("portal.templates.scopeFromTerm", "Scope: {{scope}} (from the term label)", {
                              scope: scopeLabel(scope),
                            })}
                      </div>
                    ) : (
                      <Badge variant="warning" className="mt-1">
                        {t("portal.templates.scopeMissing", "Scope not set")}
                      </Badge>
                    ))}
                </TableCell>
                <TableCell className="min-w-[10rem]">{isReportCard ? layoutLabel(row.layout) : "—"}</TableCell>
                <TableCell>
                  <code className="text-xs">v{row.version}</code>
                </TableCell>
                <TableCell className="whitespace-nowrap text-xs text-muted-foreground">
                  <div>{formatStamp(row.updated_at)}</div>
                  <div>{t("portal.templates.updatedBy", "by {{name}}", { name: row.updated_by || "—" })}</div>
                </TableCell>
                <TableCell className="whitespace-nowrap text-right">
                  <div className="flex items-center justify-end gap-1">
                    <Button asChild size="sm" variant="outline">
                      <Link to={`/templates/${row.id}`} aria-label={t("portal.templates.openLabel", "Open {{name}}", { name: describe(row) })}>
                        {t("portal.templates.open", "Open")}
                      </Link>
                    </Button>
                    {isAdmin && (
                      <Button
                        size="icon"
                        variant="ghost"
                        className="h-8 w-8 text-destructive hover:text-destructive"
                        onClick={() => confirmDelete(row)}
                        disabled={del.isPending && del.variables === row.id}
                        title={t("portal.common.delete", "Delete")}
                        aria-label={t("portal.templates.deleteLabel", "Delete {{name}}", { name: describe(row) })}
                      >
                        <Trash2 />
                      </Button>
                    )}
                  </div>
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <div className="space-y-1">
          <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.templates", "Templates")}</h1>
          <p className="max-w-3xl text-sm text-muted-foreground">
            {t(
              "portal.templates.intro",
              "Report cards have one template per class, session and term: it holds the card settings (layout, signatures, what to print), while marks, rank and attendance come from the results. PSEB admit cards have one template per class with the exam centre and date sheet.",
            )}
          </p>
        </div>
        {isAdmin && (
          <Button onClick={() => setNewOpen(true)}>
            <Plus /> {t("portal.templates.new", "New template")}
          </Button>
        )}
      </div>

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3 space-y-0">
          <CardTitle>{t("portal.templates.savedCount", "Saved templates ({{n}})", { n: rows.length })}</CardTitle>
          <div className="flex items-center gap-2">
            <Label htmlFor={filterId} className="text-muted-foreground">
              {t("portal.templates.session", "Session")}
            </Label>
            <Select value={sessionFilter} onValueChange={setSessionFilter}>
              <SelectTrigger id={filterId} className="h-8 w-48">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={ALL_SESSIONS}>{t("portal.templates.allSessions", "All sessions")}</SelectItem>
                {sessionOptions.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s === currentSession ? t("portal.templates.currentSession", "{{session}} (current)", { session: s }) : s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>{body}</CardContent>
      </Card>

      {isAdmin && (
        <NewTemplateDialog
          open={newOpen}
          onOpenChange={setNewOpen}
          templates={templates}
          // Keep the new rows in view when the list is filtered to another session.
          onBulkCreated={(session) => setSessionFilter((f) => (f === ALL_SESSIONS ? f : session))}
        />
      )}
    </div>
  );
}

function NewTemplateDialog({
  open, onOpenChange, templates, onBulkCreated,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  templates: PdfTemplate[];
  onBulkCreated: (session: string) => void;
}) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl">
        {/* Lives inside the content, so every opening starts from a fresh form. */}
        <NewTemplateForm templates={templates} onClose={() => onOpenChange(false)} onBulkCreated={onBulkCreated} />
      </DialogContent>
    </Dialog>
  );
}

function NewTemplateForm({
  templates, onClose, onBulkCreated,
}: {
  templates: PdfTemplate[];
  onClose: () => void;
  onBulkCreated: (session: string) => void;
}) {
  const { t } = useTranslation();
  const nav = useNavigate();
  const qc = useQueryClient();
  const currentSession = useCurrentSessionName();
  const { scopeLabel, layoutLabel, layoutHint } = useReportCardLabels();
  const uid = useId();
  const fieldId = (name: string) => `${uid}-${name}`;

  const [kind, setKind] = useState<PdfTemplateKind>("report-card");
  const [sessionPick, setSessionPick] = useState("");
  const session = sessionPick || currentSession;
  const [scope, setScope] = useState<ResultScope>("term1");
  const [layout, setLayout] = useState<ReportLayout>("summary");
  const [term, setTerm] = useState("");
  const [picked, setPicked] = useState<ReadonlySet<string>>(() => new Set(CLASSES));
  const [psebClass, setPsebClass] = useState("");

  const isReportCard = kind === "report-card";
  const chosen = CLASSES.filter((c) => picked.has(c));
  const allChosen = chosen.length === CLASSES.length;
  const termLabel = term.trim();

  // Classes that already have a report card for this session and scope (an older template
  // counts by its term label, as on the server); the server skips them.
  const existing = useMemo(() => {
    const m = new Map<string, PdfTemplate>();
    for (const x of templates) {
      if (x.kind === "report-card" && x.session === session && templateScope(x) === scope) m.set(x.class_name, x);
    }
    return m;
  }, [templates, session, scope]);
  const clashes = chosen.filter((c) => existing.has(c));
  const onlyClash = chosen.length === 1 ? existing.get(chosen[0]) : undefined;

  const toggleClass = (cls: string, on: boolean) =>
    setPicked((prev) => {
      const next = new Set(prev);
      if (on) next.add(cls);
      else next.delete(cls);
      return next;
    });

  const refresh = () => {
    qc.invalidateQueries({ queryKey: ["pdf-templates"] });
    qc.invalidateQueries({ queryKey: ["pdf-template-resolve"] });
  };

  const createOne = useMutation({
    mutationFn: (body: CreateBody) => api.post<PdfTemplate>("/pdf/templates", body).then((r) => r.data),
    onSuccess: (created) => {
      refresh();
      toast(t("portal.templates.createdFor", "Template created for {{cls}}", { cls: created.class_name }), "success");
      nav(`/templates/${created.id}`);
      onClose();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const createMany = useMutation({
    mutationFn: (body: BulkCreateBody) =>
      api.post<PdfTemplateBulkCreateResult>("/pdf/templates/bulk-create", body).then((r) => r.data),
    onSuccess: (res, body) => {
      refresh();
      const created = t("portal.templates.created", "{{n}} created", { n: res.created.length });
      const skipped = res.skipped.length
        ? t("portal.templates.skippedClasses", "{{n}} skipped ({{classes}})", {
            n: res.skipped.length,
            classes: res.skipped.map((s) => s.class_name).join(", "),
          })
        : t("portal.templates.skipped", "{{n}} skipped", { n: 0 });
      toast(`${created} · ${skipped}`, res.created.length ? "success" : "warning");
      onBulkCreated(body.session);
      onClose();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const busy = createOne.isPending || createMany.isPending;
  const canCreate = !!session && (isReportCard ? chosen.length > 0 : !!psebClass);

  const submit = () => {
    if (busy || !canCreate) return;
    if (!isReportCard) {
      createOne.mutate({ kind: "pseb-admit-card", class_name: psebClass, session, term: null, data: PSEB_SEED });
      return;
    }
    const common = { session, scope, layout, ...(termLabel ? { term: termLabel } : {}), data: {} };
    if (chosen.length === 1) {
      createOne.mutate({ kind: "report-card", class_name: chosen[0], ...common });
    } else {
      // Every class ticked → null, so the server uses its own full class list.
      createMany.mutate({ kind: "report-card", ...common, class_names: allChosen ? null : chosen });
    }
  };

  const createLabel = busy
    ? t("portal.templates.creating", "Creating…")
    : isReportCard && chosen.length > 1
      ? t("portal.templates.createMany", "Create {{n}} templates", { n: chosen.length })
      : t("portal.templates.create", "Create template");

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault();
        submit();
      }}
      className="space-y-4"
    >
      <DialogHeader>
        <DialogTitle>{t("portal.templates.new", "New template")}</DialogTitle>
        <DialogDescription>
          {isReportCard
            ? t(
                "portal.templates.newHintReportCard",
                "One report-card template per class for the chosen session and term. Signatures and what the card shows are set on the template's page afterwards.",
              )
            : t(
                "portal.templates.newHintPseb",
                "One admit-card template per class and session. The exam centre and date sheet are filled in on the next screen.",
              )}
        </DialogDescription>
      </DialogHeader>

      <div className="grid gap-4 sm:grid-cols-2">
        <div className="space-y-1.5">
          <Label htmlFor={fieldId("kind")}>{t("portal.templates.kind", "Kind")}</Label>
          <Select value={kind} onValueChange={(v) => setKind(v as PdfTemplateKind)}>
            <SelectTrigger id={fieldId("kind")}>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="report-card">{t("portal.templates.kindReportCard", "Report card")}</SelectItem>
              <SelectItem value="pseb-admit-card">{t("portal.templates.kindPseb", "PSEB admit card")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor={fieldId("session")}>{t("portal.templates.session", "Session")}</Label>
          <SessionSelect id={fieldId("session")} value={session} onChange={setSessionPick} />
        </div>
      </div>

      {isReportCard ? (
        <>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor={fieldId("scope")}>{t("portal.templates.scope", "Scope")}</Label>
              <Select value={scope} onValueChange={(v) => setScope(v as ResultScope)}>
                <SelectTrigger id={fieldId("scope")}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SCOPES.map((s) => (
                    <SelectItem key={s} value={s}>
                      {scopeLabel(s)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {t("portal.templates.scopeHint", "Which marks the card adds up: one term's exams, or the whole year.")}
              </p>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={fieldId("term")}>{t("portal.templates.termLabel", "Term label (optional)")}</Label>
              <Input
                id={fieldId("term")}
                value={term}
                maxLength={TERM_LABEL_MAX}
                placeholder={DEFAULT_TERM_LABEL[scope]}
                onChange={(e) => setTerm(e.target.value)}
                // Enter here would submit the form and could create a template for every class.
                onKeyDown={(e) => {
                  if (e.key === "Enter") e.preventDefault();
                }}
              />
              <p className="text-xs text-muted-foreground">
                {t("portal.templates.termLabelHint", "Printed in the card's title. Leave blank for “{{label}}”.", {
                  label: DEFAULT_TERM_LABEL[scope],
                })}
              </p>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label htmlFor={fieldId("layout")}>{t("portal.templates.layout", "Layout")}</Label>
            <Select value={layout} onValueChange={(v) => setLayout(v as ReportLayout)}>
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
            <p className="text-xs text-muted-foreground">{layoutHint(layout, scope)}</p>
          </div>

          <div role="group" aria-labelledby={fieldId("classes")} className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <span id={fieldId("classes")} className="text-sm font-medium">
                {t("portal.templates.classes", "Classes")}
              </span>
              <label className="flex cursor-pointer items-center gap-2 text-sm">
                <Checkbox
                  checked={allChosen}
                  onCheckedChange={(v) => setPicked(v === true ? new Set(CLASSES) : new Set())}
                />
                {t("portal.templates.allClasses", "All classes")}
              </label>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-2 rounded-md border p-3 sm:grid-cols-4 md:grid-cols-5">
              {CLASSES.map((c) => (
                <label key={c} className="flex cursor-pointer items-center gap-2 text-sm">
                  <Checkbox checked={picked.has(c)} onCheckedChange={(v) => toggleClass(c, v === true)} />
                  <span>{c}</span>
                  {existing.has(c) && (
                    <span
                      className="inline-flex text-muted-foreground"
                      title={t("portal.templates.hasTemplate", "Already has a {{scope}} template for {{session}}", {
                        scope: scopeLabel(scope),
                        session,
                      })}
                    >
                      <FileCheck2 className="h-3.5 w-3.5" aria-hidden />
                      <span className="sr-only">
                        {t("portal.templates.hasTemplate", "Already has a {{scope}} template for {{session}}", {
                          scope: scopeLabel(scope),
                          session,
                        })}
                      </span>
                    </span>
                  )}
                </label>
              ))}
            </div>
            <p className="text-xs text-muted-foreground">
              {t("portal.templates.classesChosen", "{{n}} of {{total}} classes selected", {
                n: chosen.length,
                total: CLASSES.length,
              })}
            </p>
            {chosen.length === 0 && (
              <p className="text-xs text-destructive">{t("portal.templates.pickAClass", "Pick at least one class.")}</p>
            )}
            {onlyClash ? (
              <p className="text-xs text-muted-foreground">
                {t("portal.templates.oneExists", "{{cls}} already has a {{scope}} template for {{session}}.", {
                  cls: onlyClash.class_name,
                  scope: scopeLabel(scope),
                  session,
                })}{" "}
                <Link to={`/templates/${onlyClash.id}`} onClick={onClose} className="font-medium text-primary underline underline-offset-4">
                  {t("portal.templates.openIt", "Open it")}
                </Link>
              </p>
            ) : (
              clashes.length > 0 && (
                <p className="text-xs text-muted-foreground">
                  {t(
                    "portal.templates.someExist",
                    "{{count}} of these classes already have a {{scope}} template for {{session}} and will be skipped: {{classes}}.",
                    { count: clashes.length, scope: scopeLabel(scope), session, classes: clashes.join(", ") },
                  )}
                </p>
              )
            )}
          </div>
        </>
      ) : (
        <div className="space-y-1.5">
          <Label htmlFor={fieldId("class")}>{t("portal.templates.class", "Class")}</Label>
          <Select value={psebClass} onValueChange={setPsebClass}>
            <SelectTrigger id={fieldId("class")}>
              <SelectValue placeholder={t("portal.templates.pickClass", "Select class")} />
            </SelectTrigger>
            <SelectContent>
              {CLASSES.map((c) => (
                <SelectItem key={c} value={c}>
                  {c}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      )}

      <DialogFooter>
        <Button type="button" variant="outline" onClick={onClose}>
          {t("portal.common.cancel", "Cancel")}
        </Button>
        <Button type="submit" disabled={!canCreate || busy}>
          {busy ? <Spinner /> : <Plus />} {createLabel}
        </Button>
      </DialogFooter>
    </form>
  );
}
