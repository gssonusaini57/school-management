import { Fragment, useId, useMemo, useState, type Dispatch, type SetStateAction } from "react";
import { useSearchParams } from "react-router-dom";
import axios from "axios";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Download, GraduationCap, Lock, Printer, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SessionSelect } from "@/components/SessionSelect";
import { ReportCardsTab } from "@/components/report-cards/ReportCardsTab";
import { useReportCardLabels } from "@/components/report-cards/labels";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatNumber } from "@/lib/format";
import { useMeta } from "@/lib/meta";
import { isClientError } from "@/lib/pdf";
import { currentSessionRow, useCurrentSessionName, useSessions } from "@/lib/session";
import { useSSE } from "@/lib/sse";
import { confirmLeave } from "@/lib/unsaved";
import { CLASSES, cn, formatDate } from "@/lib/utils";
import type {
  AcademicSession, ClassResults, ResultCell, ResultScope, StudentResult, SubjectColumn,
  SubjectResult,
} from "@/types/api";

type Tab = "results" | "report-cards";

const SCOPES: ResultScope[] = ["term1", "term2", "annual"];

/** A4 landscape for this page only: the <style> holding it lives as long as the page is mounted. */
const PRINT_CSS = `
@page { size: A4 landscape; margin: 10mm; }
@media print {
  /* Browsers drop backgrounds when printing; keep the status dots, badges and header tint. */
  .results-print-area { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
}
`;

// Sticky cells need an opaque background, or the columns scrolling under them show
// through. bg-card plus a translucent layer of the header/row tint matches the cells
// beside them. The roll column is a fixed 64px (w-16), so the student column sticks at left-16.
const STICKY_HEAD =
  "sticky z-10 bg-card [background-image:linear-gradient(hsl(var(--muted)/0.4),hsl(var(--muted)/0.4))] print:static";
const STICKY_CELL =
  "sticky z-10 bg-card group-hover:[background-image:linear-gradient(hsl(var(--muted)/0.5),hsl(var(--muted)/0.5))] print:static";
const ROLL_COL = "left-0 w-16 px-2";
const STUDENT_COL = "left-16 px-2 shadow-[inset_-1px_0_0_hsl(var(--border))]";
const HEAD_CELL = "h-auto px-2 py-2 text-center align-bottom";
// A mark below the pass mark is underlined as well as red: colour alone is lost to a
// colour-blind reader and on a black-and-white print, and every total is bold per exam.
const FAILING_MARK = "underline decoration-2 underline-offset-2";
const NUM_CELL = "whitespace-nowrap px-2 py-2 text-center tabular-nums";

interface ViewOptions {
  showExams: boolean;
  includeDrafts: boolean;
  hideNoMarks: boolean;
}

/** One per-exam column of a subject: an index into ClassResults.groups and SubjectResult.cells. */
interface ExamColumn {
  index: number;
  label: string;
  max: number;
}

interface SubjectView {
  col: SubjectColumn;
  exams: ExamColumn[]; // [] = the subject is a single column
}

interface Row {
  st: StudentResult;
  subjects: Map<string, SubjectResult>;
}

/** Today as YYYY-MM-DD on the local calendar (the school and its staff are on IST). */
function todayIso(d: Date = new Date()): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

/** Term 1 or Term 2 while today falls inside that term of the current session, else Annual. */
function scopeForToday(sessions: AcademicSession[] | undefined): ResultScope {
  const current = currentSessionRow(sessions);
  if (!current) return "annual";
  const today = todayIso();
  const within = (start: string, end: string) =>
    !!start && !!end && start.slice(0, 10) <= today && today <= end.slice(0, 10);
  if (within(current.term1_start, current.term1_end)) return "term1";
  if (within(current.term2_start, current.term2_end)) return "term2";
  return "annual";
}

/** A subject total or an exam cell as printed: "" when nothing counted is entered. */
function markText(m: { obtained: number; status: string } | undefined): string {
  return !m || m.status === "missing" || m.status === "none" ? "" : formatNumber(m.obtained);
}

/** A graded subject's letter; on the annual scope "A1 / B2" when both terms have one. */
function gradeText(sub: SubjectResult | undefined, annual: boolean): string {
  if (!sub) return "";
  if (annual) {
    const first = sub.term_letters["1"];
    const second = sub.term_letters["2"];
    if (first && second) return `${first} / ${second}`;
  }
  return sub.grade_letter ?? "";
}

/**
 * The columns of each subject. With "Show each exam" a numeric subject gets one
 * column per exam group it has (P.T. First, …; Term 1 / Term 2 on the annual scope)
 * followed by its total; graded subjects always stay a single column.
 */
function subjectViews(
  data: ClassResults,
  rows: Row[],
  showExams: boolean,
  groupLabel: (index: number) => string,
): SubjectView[] {
  return data.subject_columns.map((col) => {
    if (!showExams || col.is_grading) return { col, exams: [] };
    const exams: ExamColumn[] = [];
    data.groups.forEach((_, index) => {
      // Which exams a subject has doesn't depend on the student, so the first row
      // carrying the subject tells whether it uses this column, and the column's max.
      let cell: ResultCell | undefined;
      for (const r of rows) {
        cell = r.subjects.get(col.subject_name)?.cells[index];
        if (cell) break;
      }
      if (cell && cell.status !== "none") exams.push({ index, label: groupLabel(index), max: cell.max });
    });
    return { col, exams };
  });
}

function csvCell(value: string): string {
  // Spreadsheets run a cell that starts with = + - @ as a formula.
  const v = /^[=+\-@\t\r]/.test(value) ? `'${value}` : value;
  return /[",\r\n]/.test(v) ? `"${v.replace(/"/g, '""')}"` : v;
}

function downloadCsv(rows: string[][], filename: string): void {
  // The BOM makes Excel read the file as UTF-8 (Punjabi names, "—") instead of the system code page.
  const csv = "﻿" + rows.map((r) => r.map(csvCell).join(",")).join("\r\n");
  const url = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

const fileSafe = (s: string) => s.replace(/[^A-Za-z0-9._-]+/g, "_");

/** A CSV cell for a mark or letter: "25*" when some of its exams aren't entered yet. */
function csvMark(text: string, status: string | undefined): string {
  return text && status === "partial" ? `${text}*` : text;
}

/**
 * The visible table as CSV rows: the same rows and columns as on screen, with
 * "obtained/max" split into Total and Max so spreadsheets read numbers, not dates.
 * The screen's markers come along, so a shared file can't pass for final results:
 * a first line while the results are provisional or include drafts, "(Draft)" on
 * subjects with unsubmitted marks, "*" on part-entered marks, and a legend.
 */
function resultsCsvRows(
  views: SubjectView[],
  rows: Row[],
  labels: ResultLabels,
  annual: boolean,
  state: { complete: boolean; draftsIncluded: boolean },
): string[][] {
  const header = [labels.roll, labels.student];
  for (const v of views) {
    const name = v.col.subject_name;
    const draftTag = v.col.batch_status === "draft" ? ` (${labels.draft})` : "";
    if (v.exams.length) {
      for (const e of v.exams) header.push(`${name} — ${e.label} (/${formatNumber(e.max)})${draftTag}`);
      header.push(`${name} — ${labels.total} (/${formatNumber(v.col.max)})${draftTag}`);
    } else {
      header.push((v.col.is_grading ? `${name} (${labels.grade})` : `${name} (/${formatNumber(v.col.max)})`) + draftTag);
    }
  }
  header.push(labels.total, labels.max, labels.percentage, labels.grade, labels.rank, labels.attendance);
  if (annual) header.push(labels.result);

  const notes = [
    ...(state.complete ? [] : [labels.provisional]),
    ...(state.draftsIncluded ? [labels.draftsIncluded] : []),
  ];
  const lines: string[][] = notes.length ? [[notes.join(" · ")], [], header] : [header];
  let partial = false;
  let draft = false;
  for (const { st, subjects } of rows) {
    const line = [st.roll_no ?? "", st.name];
    for (const v of views) {
      const sub = subjects.get(v.col.subject_name);
      if (v.col.batch_status === "draft") draft = true;
      for (const e of v.exams) {
        const cell = sub?.cells[e.index];
        if (cell?.status === "partial") partial = true;
        line.push(csvMark(markText(cell), cell?.status));
      }
      if (sub?.status === "partial") partial = true;
      line.push(csvMark(v.col.is_grading ? gradeText(sub, annual) : markText(sub), sub?.status));
    }
    line.push(
      st.has_marks ? formatNumber(st.total_obtained) : "",
      st.has_marks ? formatNumber(st.total_max) : "",
      st.has_marks && st.percentage != null ? formatNumber(st.percentage, 2) : "",
      st.has_marks ? st.grade ?? "" : "",
      st.rank != null ? String(st.rank) : "",
      st.attendance?.pct != null ? formatNumber(st.attendance.pct) : "",
    );
    if (annual) line.push(st.promotion ? labels.promotion(st.promotion) : "");
    lines.push(line);
  }
  if (partial || draft) lines.push([]);
  if (partial) lines.push([`* ${labels.partialHint}`]);
  if (draft) lines.push([`(${labels.draft}) ${labels.draftHint}`]);
  return lines;
}

/**
 * Every label the results table and its CSV share, translated once per render.
 * `passPct` is the pass mark the results were worked out with, null while it isn't known.
 */
function useResultLabels(passPct: number | null) {
  const { t } = useTranslation();
  return {
    roll: t("portal.results.roll", "Roll"),
    student: t("portal.results.student", "Student"),
    total: t("portal.results.total", "Total"),
    max: t("portal.results.max", "Max"),
    percentage: t("portal.results.percentage", "%"),
    grade: t("portal.results.grade", "Grade"),
    rank: t("portal.results.rank", "Rank"),
    attendance: t("portal.results.attendance", "Att %"),
    result: t("portal.results.result", "Result"),
    draft: t("portal.results.draft", "Draft"),
    draftHint: t("portal.results.draftHint", "Marks not submitted yet (still a draft)"),
    missing: t("portal.results.missing", "Not entered"),
    partialHint: t("portal.results.partialHint", "Some exams not entered yet"),
    provisional: t(
      "portal.results.csvProvisional",
      "Provisional results: not every subject is entered and submitted yet, so totals and ranks can still change.",
    ),
    draftsIncluded: t("portal.results.draftsIncluded", "Draft marks included"),
    belowPass:
      passPct != null
        ? t("portal.results.belowPass", "Below the pass mark ({{pct}}%)", { pct: formatNumber(passPct) })
        : t("portal.results.belowPassNoPct", "Below the pass mark"),
    attendanceDays: (present: number, working: number) =>
      t("portal.results.attendanceDays", "{{present}} of {{working}} days present", {
        present: formatNumber(present),
        working,
      }),
    promotion: (value: string) =>
      value === "Promoted"
        ? t("portal.reportCards.promoted", "Promoted")
        : value === "Conditional"
          ? t("portal.reportCards.conditional", "Conditional")
          : value === "Detained"
            ? t("portal.reportCards.detained", "Detained")
            : value,
  };
}
type ResultLabels = ReturnType<typeof useResultLabels>;

export default function MarksResults() {
  const { t } = useTranslation();
  const { user, isAdmin } = useAuth();
  const { scopeLabel } = useReportCardLabels();
  const fieldId = useId();

  // Class, session, scope and tab live in the URL (replacing the entry), so coming
  // Back from a template or its card settings returns to the same view.
  const [searchParams, setSearchParams] = useSearchParams();
  const setParam = (key: string, value: string | null) =>
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        if (value) next.set(key, value);
        else next.delete(key);
        return next;
      },
      { replace: true },
    );

  // Staff see the classes they teach (none until an admin assigns some); admins see every class.
  const classOptions = isAdmin ? CLASSES : user?.allowed_classes ?? [];
  const classParam = searchParams.get("class") ?? "";
  const clsPick = classOptions.includes(classParam) ? classParam : "";
  // A teacher with a single class doesn't have to pick it.
  const cls = clsPick || (classOptions.length === 1 ? classOptions[0] : "");

  const sessionsQ = useSessions();
  const currentSession = useCurrentSessionName();
  const sessionPick = searchParams.get("session") ?? "";
  const session = sessionPick || currentSession;

  const scopeParam = searchParams.get("scope");
  const scopePick = SCOPES.find((s) => s === scopeParam) ?? null;
  // The default session and scope come from GET /sessions: wait for it instead of
  // loading results for a guess first, unless both were already picked by hand.
  const ready = !sessionsQ.isPending || (!!sessionPick && scopePick !== null);
  const scopeToday = scopeForToday(sessionsQ.data);
  // Until a scope is picked by hand, a class whose current term is Term 2 with no marks yet
  // opens on Term 1 (as the Android app does), with a note saying why. The probe shares
  // ResultsView's cache entry for Term 2, so it isn't fetched twice.
  const probeTerm2 = ready && !scopePick && scopeToday === "term2" && !!cls && !!session;
  const term2Q = useQuery({
    queryKey: ["results", cls, session, "term2", true] as const,
    queryFn: () =>
      api
        .get<ClassResults>("/marks/results", { params: { class: cls, session, scope: "term2", include_drafts: true } })
        .then((r) => r.data),
    enabled: probeTerm2,
    retry: (failures, e) => !isClientError(e) && failures < 1,
  });
  const term2Empty = probeTerm2 && !!term2Q.data && !term2Q.data.students.some((s) => s.has_marks);
  const probing = probeTerm2 && term2Q.isPending;
  const scope = scopePick ?? (term2Empty ? "term1" : scopeToday);

  const [view, setView] = useState<ViewOptions>({ showExams: false, includeDrafts: true, hideNoMarks: true });

  const tab: Tab = searchParams.get("tab") === "report-cards" ? "report-cards" : "results";

  // Each of these unmounts the report-card roster, so unsaved remarks or overrides are asked about first.
  const onClassChange = (value: string) => {
    if (value !== cls && confirmLeave()) setParam("class", value);
  };
  const onSessionChange = (value: string) => {
    if (value !== session && confirmLeave()) setParam("session", value);
  };
  const onScopeChange = (value: string) => {
    if (value !== scope && confirmLeave()) setParam("scope", value);
  };
  const onTabChange = (value: string) => {
    if (value !== tab && confirmLeave()) setParam("tab", value === "report-cards" ? value : null);
  };

  // A staff account without classes yet: the server refuses every class (403), so offer none.
  if (!classOptions.length) {
    return (
      <div className="space-y-4">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.marksResults", "Marks — Results")}</h1>
        <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
          <GraduationCap className="mx-auto mb-2 h-6 w-6" aria-hidden />
          {t("portal.common.noClassesAssigned", "No classes are assigned to your account yet. Ask an admin.")}
        </div>
      </div>
    );
  }

  const loading = (
    <div className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
      <Spinner /> {t("portal.common.loading", "Loading…")}
    </div>
  );

  return (
    <>
      <style>{PRINT_CSS}</style>
      <div className="space-y-4 print:space-y-0">
        <h1 className="font-display text-heading-lg text-deep-indigo print:hidden">
          {t("portal.nav.marksResults", "Marks — Results")}
        </h1>

        <Card className="print:hidden">
          <CardContent className="grid grid-cols-1 gap-3 p-4 md:grid-cols-3">
            <div className="space-y-1.5">
              <Label htmlFor={`${fieldId}-class`}>{t("portal.results.class", "Class")}</Label>
              <Select value={cls} onValueChange={onClassChange}>
                <SelectTrigger id={`${fieldId}-class`}>
                  <SelectValue placeholder={t("portal.results.selectClass", "Select a class")} />
                </SelectTrigger>
                <SelectContent>
                  {classOptions.map((c) => (
                    <SelectItem key={c} value={c}>{c}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`${fieldId}-session`}>{t("portal.results.session", "Session")}</Label>
              <SessionSelect id={`${fieldId}-session`} value={session} onChange={onSessionChange} />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor={`${fieldId}-scope`}>{t("portal.results.scope", "Scope")}</Label>
              <Select value={scope} onValueChange={onScopeChange}>
                <SelectTrigger id={`${fieldId}-scope`}>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {SCOPES.map((s) => (
                    <SelectItem key={s} value={s}>{scopeLabel(s)}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardContent>
        </Card>

        {term2Empty && (
          <p role="status" className="text-sm text-muted-foreground print:hidden">
            {t("portal.results.term2Empty", "No Term 2 marks yet, so this shows Term 1. Pick Term 2 under Scope to see it.")}
          </p>
        )}
        {/* Manual activation: a click or Enter switches tabs and focus alone doesn't, so the
            unsaved-changes prompt in onTabChange asks once, not again on the focus after a click. */}
        <Tabs value={tab} onValueChange={onTabChange} activationMode="manual">
          <TabsList className="print:hidden">
            <TabsTrigger value="results">{t("portal.results.tabResults", "Results")}</TabsTrigger>
            <TabsTrigger value="report-cards">{t("portal.reportCards.title", "Report cards")}</TabsTrigger>
          </TabsList>
          {/* Radix mounts a tab's content only while that tab is active. */}
          <TabsContent value="results" className="print:mt-0">
            {!cls ? (
              <div className="rounded-md border border-dashed p-8 text-center text-sm text-muted-foreground">
                <GraduationCap className="mx-auto mb-2 h-6 w-6" aria-hidden />
                {t("portal.results.pickClass", "Pick a class to see its results.")}
              </div>
            ) : !ready || probing ? (
              loading
            ) : (
              <ResultsView cls={cls} session={session} scope={scope} view={view} onViewChange={setView} />
            )}
          </TabsContent>
          <TabsContent value="report-cards">
            {ready && !probing ? <ReportCardsTab cls={cls} session={session} scope={scope} /> : loading}
          </TabsContent>
        </Tabs>
      </div>
    </>
  );
}

function ResultsView({
  cls,
  session,
  scope,
  view,
  onViewChange,
}: {
  cls: string;
  session: string;
  scope: ResultScope;
  view: ViewOptions;
  onViewChange: Dispatch<SetStateAction<ViewOptions>>;
}) {
  const { t } = useTranslation();
  const meta = useMeta();
  const { scopeLabel } = useReportCardLabels();
  const { showExams, includeDrafts, hideNoMarks } = view;
  const setOption = (key: keyof ViewOptions) => (value: boolean) => onViewChange((v) => ({ ...v, [key]: value }));

  const resultsQ = useQuery({
    queryKey: ["results", cls, session, scope, includeDrafts] as const,
    queryFn: () =>
      api
        .get<ClassResults>("/marks/results", { params: { class: cls, session, scope, include_drafts: includeDrafts } })
        .then((r) => r.data),
    enabled: !!cls && !!session,
    retry: (failures, e) => !isClientError(e) && failures < 1,
    // Flipping "Include draft marks" keeps the table on screen while the other version
    // loads; another class, session or scope starts from the spinner instead.
    placeholderData: (previous, previousQuery) => {
      const key = previousQuery?.queryKey;
      return key && key[1] === cls && key[2] === session && key[3] === scope ? previous : undefined;
    },
  });
  // Saving or submitting marks anywhere refreshes the table, and the report-card rosters
  // (their tab isn't mounted now, so they reload when it opens).
  useSSE("marks-batches", [["results"], ["pdf-roster"]]);
  // So does a change to the class's subjects and exams (a term, max marks or a rename moves totals).
  useSSE("class-subjects", [["results"], ["pdf-roster"]]);

  const data = resultsQ.data;
  // A results server older than this page (engine v1: no groups, cells, warnings or failed
  // subjects) answers while a deploy is half done, or after a backend-only rollback: say so
  // instead of rendering a table from fields that aren't there.
  const serverOutdated = !!data && data.engine_version == null;
  // The pass mark these results were graded with (the class's report-card rule, else the
  // school default), from the same response as the red cells it explains.
  const labels = useResultLabels(data ? data.pass_pct ?? meta.pass_pct : null);
  const allRows = useMemo<Row[]>(
    () =>
      (data?.students ?? []).map((st) => ({
        st,
        subjects: new Map(st.subjects.map((s) => [s.subject_name, s] as const)),
      })),
    [data],
  );
  const rows = hideNoMarks ? allRows.filter((r) => r.st.has_marks) : allRows;
  const hiddenCount = allRows.length - rows.length;
  const annual = data?.scope === "annual";
  const groupLabel = (index: number): string => {
    const g = data?.groups[index];
    if (!g) return "";
    if (annual && g.term === 1) return scopeLabel("term1");
    if (annual && g.term === 2) return scopeLabel("term2");
    return g.key;
  };
  const views = data && !serverOutdated ? subjectViews(data, allRows, showExams, groupLabel) : [];
  const scopeName = scopeLabel(scope);
  const forbidden = axios.isAxiosError(resultsQ.error) && resultsQ.error.response?.status === 403;
  const forbiddenText = t(
    "portal.results.forbidden",
    "You don't have access to the results of {{cls}}. Ask an admin to add this class and the Results menu to your account.",
    { cls },
  );
  // Nothing on the toolbar can help with a class outside this account's access.
  const blocked = forbidden && !data;
  const canExport = !!data && !serverOutdated && rows.length > 0;

  const exportCsv = () => {
    if (!data || serverOutdated) return;
    downloadCsv(
      resultsCsvRows(views, rows, labels, annual, {
        complete: data.complete,
        draftsIncluded: data.include_drafts && data.has_drafts,
      }),
      `results_${fileSafe(cls)}_${fileSafe(session)}_${data.scope}.csv`,
    );
  };

  return (
    <Card className="results-print-area print:border-0 print:bg-transparent print:shadow-none">
      <CardHeader className="space-y-3 pb-3 print:hidden">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2 text-deep-indigo">
            <span>
              {cls} · {scopeName} · {session}
            </span>
            {resultsQ.isFetching && !resultsQ.isPending && (
              <span role="status" className="inline-flex text-muted-foreground">
                <Spinner />
                <span className="sr-only">{t("portal.results.updating", "Updating…")}</span>
              </span>
            )}
          </CardTitle>
          {!blocked && (
            <div className="flex flex-wrap gap-2">
              <Button variant="outline" size="sm" onClick={exportCsv} disabled={!canExport}>
                <Download /> {t("portal.results.exportCsv", "Export CSV")}
              </Button>
              <Button variant="outline" size="sm" onClick={() => window.print()} disabled={!canExport}>
                <Printer /> {t("portal.results.print", "Print")}
              </Button>
            </div>
          )}
        </div>
        {!blocked && (
          <div className="flex flex-wrap items-center gap-x-5 gap-y-2">
            <Toggle
              checked={showExams}
              onChange={setOption("showExams")}
              label={t("portal.results.showComponents", "Show each exam")}
            />
            <Toggle
              checked={includeDrafts}
              onChange={setOption("includeDrafts")}
              label={t("portal.results.includeDrafts", "Include draft marks")}
            />
            <Toggle
              checked={hideNoMarks}
              onChange={setOption("hideNoMarks")}
              label={t("portal.results.hideNoMarks", "Hide students without marks")}
            />
          </div>
        )}
      </CardHeader>

      <CardContent className="space-y-3 print:space-y-2 print:p-0">
        {resultsQ.isPending ? (
          <div className="flex items-center gap-2 py-6 text-sm text-muted-foreground">
            <Spinner /> {t("portal.results.loading", "Loading results…")}
          </div>
        ) : serverOutdated ? (
          <div role="status" className="flex flex-wrap items-center gap-2 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
            <TriangleAlert className="h-4 w-4 shrink-0 text-amber-700" aria-hidden />
            <span>{t("portal.results.serverUpdating", "The server is being updated. Try again in a minute.")}</span>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => void resultsQ.refetch()}>
              {t("portal.common.tryAgain", "Try again")}
            </Button>
          </div>
        ) : !data ? (
          forbidden ? (
            <div role="alert" className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-4 text-sm text-amber-900">
              <Lock className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden />
              <span>{forbiddenText}</span>
            </div>
          ) : (
            <div role="alert" className="flex flex-wrap items-center gap-2 rounded-md bg-destructive/10 p-4 text-sm text-destructive">
              <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
              <span>
                {t("portal.results.loadError", "Couldn't load the results.")} {apiError(resultsQ.error)}
              </span>
              <Button variant="outline" size="sm" className="ml-auto" onClick={() => void resultsQ.refetch()}>
                {t("portal.common.tryAgain", "Try again")}
              </Button>
            </div>
          )
        ) : (
          <>
            <div className="hidden print:block">
              <p className="font-display text-heading-sm text-deep-indigo">
                {t("common.schoolName", "Khalsa International Senior Secondary School")}
              </p>
              <p className="text-body-sm font-semibold">
                {t("portal.results.printHeading", "Results · Class {{cls}} · Session {{session}} · {{scope}}", {
                  cls,
                  session,
                  scope: scopeName,
                })}
              </p>
              <p className="text-caption text-muted-foreground">
                {t("portal.results.printedOn", "Printed on {{date}}", { date: formatDate(new Date()) })}
              </p>
            </div>

            {resultsQ.isError && (
              <div role="alert" className="flex flex-wrap items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive print:hidden">
                <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
                <span>
                  {forbidden
                    ? forbiddenText
                    : `${t("portal.results.refreshError", "Couldn't refresh the results.")} ${apiError(resultsQ.error)}`}
                </span>
                <Button variant="outline" size="sm" className="ml-auto" onClick={() => void resultsQ.refetch()}>
                  {t("portal.common.tryAgain", "Try again")}
                </Button>
              </div>
            )}

            {!data.subject_columns.length ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                {t(
                  "portal.results.noSubjects",
                  "No subjects are set up for {{cls}} in {{scope}} yet. A super-admin can add them under Class Subjects.",
                  { cls, scope: scopeName },
                )}
              </p>
            ) : !allRows.length ? (
              <p className="py-6 text-center text-sm text-muted-foreground">
                {t("portal.results.noStudents", "No students in {{cls}} yet.", { cls })}
              </p>
            ) : (
              <>
                <div className="flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-muted-foreground print:text-caption">
                  <span>{t("portal.results.classSize", "Class size: {{n}}", { n: data.class_size })}</span>
                  <span aria-hidden>·</span>
                  <span>{t("portal.results.rankedCount", "Ranked: {{n}}", { n: data.ranked_count })}</span>
                  {hideNoMarks && hiddenCount > 0 && (
                    <>
                      <span aria-hidden>·</span>
                      <span>{t("portal.results.hiddenCount", "{{n}} without marks hidden", { n: hiddenCount })}</span>
                    </>
                  )}
                  {data.has_drafts && data.include_drafts && (
                    <Badge variant="outline" className="ml-1 border-amber-300 text-amber-800">
                      {t("portal.results.draftsIncluded", "Draft marks included")}
                    </Badge>
                  )}
                </div>

                {!data.complete && data.ranked_count > 0 && (
                  <div role="status" className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 px-3 py-2 text-sm text-amber-900 print:text-caption">
                    <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden />
                    <span>
                      {t(
                        "portal.results.provisionalNote",
                        "Ranks are provisional until every subject is entered and submitted",
                      )}
                    </span>
                  </div>
                )}

                {data.warnings.length > 0 && (
                  <div role="status" className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900 print:hidden">
                    <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" aria-hidden />
                    <ul className="space-y-0.5">
                      {data.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {rows.length ? (
                  <>
                    <ResultsTable
                      data={data}
                      views={views}
                      rows={rows}
                      labels={labels}
                      caption={t("portal.results.caption", "Results for {{cls}}, {{scope}}, session {{session}}", {
                        cls,
                        scope: scopeName,
                        session,
                      })}
                    />
                    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-muted-foreground print:text-caption">
                      <div className="inline-flex items-center gap-1.5">
                        <PartialDot /> {labels.partialHint}
                      </div>
                      <div className="inline-flex items-center gap-1.5">
                        <span aria-hidden>—</span> {labels.missing}
                      </div>
                      <div className="inline-flex items-center gap-1.5 font-semibold text-destructive">
                        <span className={FAILING_MARK}>{labels.belowPass}</span>
                      </div>
                      {views.some((v) => v.col.batch_status === "draft") && (
                        <div className="inline-flex items-center gap-1.5">
                          <DraftBadge labels={labels} /> {labels.draftHint}
                        </div>
                      )}
                    </div>
                  </>
                ) : (
                  <div className="space-y-3 py-6 text-center text-sm text-muted-foreground">
                    <p>
                      {t("portal.results.noMarks", "No marks entered for {{cls}} · {{scope}} in {{session}} yet.", {
                        cls,
                        scope: scopeName,
                        session,
                      })}
                    </p>
                    <Button variant="outline" size="sm" className="print:hidden" onClick={() => setOption("hideNoMarks")(false)}>
                      {t("portal.results.showAll", "Show all students")}
                    </Button>
                  </div>
                )}
              </>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}

function ResultsTable({
  data,
  views,
  rows,
  labels,
  caption,
}: {
  data: ClassResults;
  views: SubjectView[];
  rows: Row[];
  labels: ResultLabels;
  caption: string;
}) {
  const annual = data.scope === "annual";
  const twoRows = views.some((v) => v.exams.length > 0);
  const headRows = twoRows ? 2 : 1;
  // With per-exam columns, a line in front of every subject keeps its exams together.
  const divided = twoRows;

  return (
    <div className="relative w-full overflow-x-auto print:overflow-visible">
      <table className="w-full caption-bottom text-sm print:text-caption print:[&_td]:px-1 print:[&_td]:py-0.5 print:[&_th]:px-1 print:[&_th]:py-0.5">
        <caption className="sr-only">{caption}</caption>
        <TableHeader>
          <TableRow className="hover:bg-transparent">
            <TableHead rowSpan={headRows} className={cn(HEAD_CELL, STICKY_HEAD, ROLL_COL, "text-left")}>
              <div className="w-12 truncate">{labels.roll}</div>
            </TableHead>
            <TableHead rowSpan={headRows} className={cn(HEAD_CELL, STICKY_HEAD, STUDENT_COL, "text-left")}>
              {labels.student}
            </TableHead>
            {views.map((v) => (
              <TableHead
                key={v.col.subject_name}
                colSpan={v.exams.length ? v.exams.length + 1 : 1}
                rowSpan={v.exams.length ? 1 : headRows}
                className={cn(HEAD_CELL, "min-w-16", divided && "border-l")}
              >
                <SubjectHeading col={v.col} showMax={!v.exams.length} labels={labels} />
              </TableHead>
            ))}
            <TableHead rowSpan={headRows} className={cn(HEAD_CELL, "border-l")}>{labels.total}</TableHead>
            <TableHead rowSpan={headRows} className={HEAD_CELL}>{labels.percentage}</TableHead>
            <TableHead rowSpan={headRows} className={HEAD_CELL}>{labels.grade}</TableHead>
            <TableHead rowSpan={headRows} className={HEAD_CELL}>{labels.rank}</TableHead>
            <TableHead rowSpan={headRows} className={cn(HEAD_CELL, "whitespace-nowrap")}>{labels.attendance}</TableHead>
            {annual && <TableHead rowSpan={headRows} className={HEAD_CELL}>{labels.result}</TableHead>}
          </TableRow>
          {twoRows && (
            <TableRow className="hover:bg-transparent">
              {views.map((v) =>
                v.exams.length ? (
                  <Fragment key={v.col.subject_name}>
                    {v.exams.map((e, i) => (
                      <TableHead key={e.index} className={cn(HEAD_CELL, "py-1.5", i === 0 && "border-l")}>
                        <span className="block">{e.label}</span>
                        <span className="block font-normal normal-case tracking-normal">/{formatNumber(e.max)}</span>
                      </TableHead>
                    ))}
                    <TableHead className={cn(HEAD_CELL, "py-1.5")}>
                      <span className="block">{labels.total}</span>
                      <span className="block font-normal normal-case tracking-normal">/{formatNumber(v.col.max)}</span>
                    </TableHead>
                  </Fragment>
                ) : null,
              )}
            </TableRow>
          )}
        </TableHeader>
        <TableBody>
          {rows.map(({ st, subjects }) => (
            <TableRow key={st.student_id} className="group print:break-inside-avoid">
              <TableCell className={cn(STICKY_CELL, ROLL_COL, "py-2 tabular-nums text-muted-foreground")}>
                <div className="w-12 truncate" title={st.roll_no ?? undefined}>{st.roll_no || "—"}</div>
              </TableCell>
              <TableCell className={cn(STICKY_CELL, STUDENT_COL, "whitespace-nowrap py-2 font-medium")}>{st.name}</TableCell>
              {views.map((v) => (
                <SubjectCells
                  key={v.col.subject_name}
                  view={v}
                  sub={subjects.get(v.col.subject_name)}
                  annual={annual}
                  divided={divided}
                  failed={st.failed_subjects.includes(v.col.subject_name)}
                  labels={labels}
                />
              ))}
              <TableCell className={cn(NUM_CELL, "border-l")}>
                {st.has_marks ? (
                  <>
                    <span className="font-semibold">{formatNumber(st.total_obtained)}</span>
                    <span className="text-muted-foreground">/{formatNumber(st.total_max)}</span>
                  </>
                ) : (
                  <Dash />
                )}
              </TableCell>
              <TableCell className={NUM_CELL}>
                {/* Two decimals, as the card prints it: one would show 90.95 as 91, past its grade's band. */}
                {st.has_marks && st.percentage != null ? `${formatNumber(st.percentage, 2)}%` : <Dash />}
              </TableCell>
              <TableCell className={NUM_CELL}>
                {st.has_marks && st.grade ? <span className="font-semibold">{st.grade}</span> : <Dash />}
              </TableCell>
              <TableCell className={NUM_CELL}>{st.rank != null ? st.rank : <Dash />}</TableCell>
              <TableCell
                className={NUM_CELL}
                title={st.attendance ? labels.attendanceDays(st.attendance.days_present, st.attendance.working_days) : undefined}
              >
                {st.attendance?.pct != null ? `${formatNumber(st.attendance.pct)}%` : <Dash />}
              </TableCell>
              {annual && (
                <TableCell className={NUM_CELL}>
                  {st.promotion ? <PromotionBadge value={st.promotion} label={labels.promotion(st.promotion)} /> : <Dash />}
                </TableCell>
              )}
            </TableRow>
          ))}
        </TableBody>
      </table>
    </div>
  );
}

function SubjectHeading({ col, showMax, labels }: { col: SubjectColumn; showMax: boolean; labels: ResultLabels }) {
  return (
    <div className="flex flex-col items-center gap-0.5">
      <span>{col.subject_name}</span>
      {col.subject_name_pa && (
        <span lang="pa" className="font-normal normal-case tracking-normal">
          {col.subject_name_pa}
        </span>
      )}
      {showMax && (
        <span className="font-normal normal-case tracking-normal">
          {col.is_grading ? labels.grade : `/${formatNumber(col.max)}`}
        </span>
      )}
      {col.batch_status === "draft" && <DraftBadge labels={labels} />}
    </div>
  );
}

function SubjectCells({
  view,
  sub,
  annual,
  divided,
  failed,
  labels,
}: {
  view: SubjectView;
  sub: SubjectResult | undefined;
  annual: boolean;
  divided: boolean;
  failed: boolean; // the server counts this subject among the student's failed ones
  labels: ResultLabels;
}) {
  const { col, exams } = view;
  if (col.is_grading) {
    return (
      <TableCell className={cn(NUM_CELL, divided && "border-l")}>
        <MarkValue status={sub?.status ?? "missing"} text={gradeText(sub, annual)} labels={labels} />
      </TableCell>
    );
  }
  // The verdict of /marks/results, made with the pass mark of the class's own rule.
  const total = (
    <TableCell className={cn(NUM_CELL, exams.length > 0 ? "font-semibold" : divided && "border-l")}>
      <MarkValue status={sub?.status ?? "missing"} text={markText(sub)} failing={failed} labels={labels} />
    </TableCell>
  );
  if (!exams.length) return total;
  return (
    <>
      {exams.map((e, i) => {
        const cell = sub?.cells[e.index];
        return (
          <TableCell key={e.index} className={cn(NUM_CELL, i === 0 && "border-l")}>
            <MarkValue status={cell?.status ?? "missing"} text={markText(cell)} labels={labels} />
          </TableCell>
        );
      })}
      {total}
    </>
  );
}

function MarkValue({
  status,
  text,
  failing = false,
  labels,
}: {
  status: string;
  text: string;
  failing?: boolean;
  labels: ResultLabels;
}) {
  if (!text || status === "missing" || status === "none") {
    return (
      <span className="font-normal text-muted-foreground" title={labels.missing}>
        <span aria-hidden>—</span>
        <span className="sr-only">{labels.missing}</span>
      </span>
    );
  }
  const partial = status === "partial";
  const hint = partial ? labels.partialHint : failing ? labels.belowPass : undefined;
  return (
    <span className={cn("inline-flex items-center gap-1", failing && "font-semibold text-destructive")} title={hint}>
      {partial && <PartialDot />}
      {failing ? <span className={FAILING_MARK}>{text}</span> : text}
      {hint && <span className="sr-only"> ({hint})</span>}
    </span>
  );
}

function PartialDot() {
  return <span aria-hidden className="inline-block h-1.5 w-1.5 shrink-0 rounded-full bg-amber-500" />;
}

function DraftBadge({ labels }: { labels: ResultLabels }) {
  return (
    <Badge variant="outline" className="border-amber-300 px-1.5 py-0 normal-case tracking-normal text-amber-800" title={labels.draftHint}>
      {labels.draft}
    </Badge>
  );
}

function PromotionBadge({ value, label }: { value: string; label: string }) {
  if (value === "Promoted") return <Badge variant="success">{label}</Badge>;
  if (value === "Conditional") return <Badge variant="warning">{label}</Badge>;
  if (value === "Detained") {
    // Tinted rather than solid red: white-on-red text vanishes when backgrounds don't print.
    return (
      <Badge variant="outline" className="border-transparent bg-destructive/10 text-destructive">
        {label}
      </Badge>
    );
  }
  return <Badge variant="outline">{label}</Badge>;
}

function Dash() {
  return <span className="text-muted-foreground">—</span>;
}

function Toggle({ checked, onChange, label }: { checked: boolean; onChange: (value: boolean) => void; label: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-sm">
      <Checkbox checked={checked} onCheckedChange={(v) => onChange(v === true)} />
      {label}
    </label>
  );
}
