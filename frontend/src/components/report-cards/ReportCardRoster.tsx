import { Fragment, useEffect, useMemo, useState } from "react";
import axios from "axios";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Download, Eye, Layers, RefreshCw, Save, SlidersHorizontal, TriangleAlert, Undo2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { NumberField } from "@/components/ui/number-field";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Spinner } from "@/components/ui/spinner";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { formatNumber } from "@/lib/format";
import { useMeta } from "@/lib/meta";
import {
  REMARK_MAX, downloadCachedPdf, isClientError, isRenderJobActive, openReportCardPreview, renderJobQuery,
  templateRosterQuery,
} from "@/lib/pdf";
import { useSSE } from "@/lib/sse";
import { useUnsavedChanges } from "@/lib/unsaved";
import { cn } from "@/lib/utils";
import type {
  PdfRenderResultRow, PdfStudentDataRow, PdfStudentRosterRow, PdfTemplate,
  RenderJob, ReportCardStudentData, ReportCardTemplateData,
} from "@/types/api";
import { RenderJobProgress } from "./RenderJobProgress";
import { useReportCardLabels } from "./labels";

/** Select sentinels: a Radix item value can never be "". */
const NO_HOUSE = "__none__";
const AUTO_PROMOTION = "__auto__";
const COLUMNS = 11;
const SYNC_RENDER_TIMEOUT_MS = 2 * 60_000;

/** Everything the roster edits for one student, as the strings its inputs hold. */
interface Draft {
  remarksEn: string;
  remarksPa: string;
  house: string; // "" = no house
  // Overrides; "" = print the computed value.
  rank: string;
  classSize: string;
  attendancePct: string;
  workingDays: string;
  daysPresent: string;
  promotion: string; // "" = automatic
}
type DraftKey = keyof Draft;
/** Only the fields a person touched, per student id. */
type Edits = Record<number, Partial<Draft>>;
type OverrideNumberKey = "rank" | "classSize" | "attendancePct" | "workingDays" | "daysPresent";
type StudentDataPatch = Partial<ReportCardStudentData>;
type Problem = "englishRemarkMissing" | "daysPresentOverWorkingDays";

interface PendingRow {
  id: number;
  data: StudentDataPatch; // just the changed keys, ready for PUT
  problems: Problem[];
}

const EMPTY_DRAFT: Draft = {
  remarksEn: "", remarksPa: "", house: "",
  rank: "", classSize: "", attendancePct: "", workingDays: "", daysPresent: "", promotion: "",
};

// Bounds mirror ReportCardStudentData on the server (rank/classSize ≥ 1, attendance 0–100, …).
const OVERRIDE_FIELDS: { key: OverrideNumberKey; min: number; max?: number; integer: boolean }[] = [
  { key: "rank", min: 1, integer: true },
  { key: "classSize", min: 1, integer: true },
  { key: "attendancePct", min: 0, max: 100, integer: false },
  { key: "workingDays", min: 0, integer: true },
  { key: "daysPresent", min: 0, integer: false }, // a half day counts 0.5
];
const OVERRIDE_KEYS = OVERRIDE_FIELDS.map((f) => f.key);

function toDraft(d: ReportCardStudentData | undefined): Draft {
  const num = (v: number | null | undefined) => (v == null ? "" : String(v));
  return {
    remarksEn: d?.remarks?.en ?? "",
    remarksPa: d?.remarks?.pa ?? "",
    house: d?.house ?? "",
    rank: num(d?.rank),
    classSize: num(d?.classSize),
    attendancePct: num(d?.attendancePct),
    workingDays: num(d?.workingDays),
    daysPresent: num(d?.daysPresent),
    promotion: d?.promotion ?? "",
  };
}

function parseNumber(s: string): number | null {
  const v = s.trim();
  if (!v) return null;
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

/** The keys that differ from what is saved. Staff never send override keys (the server 422s them). */
function buildPatch(base: Draft, cur: Draft, isAdmin: boolean): StudentDataPatch {
  const patch: StudentDataPatch = {};
  const en = cur.remarksEn.trim();
  const pa = cur.remarksPa.trim();
  if (en !== base.remarksEn.trim() || pa !== base.remarksPa.trim()) {
    // The English line is the remark; without it there is no remark.
    patch.remarks = en ? { en, pa: pa || null } : null;
  }
  if (cur.house !== base.house) patch.house = cur.house || null;
  if (isAdmin) {
    for (const key of OVERRIDE_KEYS) {
      const next = parseNumber(cur[key]);
      if (next !== parseNumber(base[key])) patch[key] = next;
    }
    if (cur.promotion !== base.promotion) patch.promotion = cur.promotion || null;
  }
  return patch;
}

/** Python's round(x, 1), as the card uses it: the nearest tenth, an exact tie going to the even digit. */
function roundTenth(x: number): number {
  // Only x.25 and x.75 are exact ties in binary: toFixed sends them up, Python to the even tenth.
  if (Number.isInteger(x * 4) && !Number.isInteger(x * 2)) {
    const down = Math.floor(x * 10);
    return (down % 2 === 0 ? down : down + 1) / 10;
  }
  return Number(x.toFixed(1));
}

interface CardAttendance {
  pct: number | null;
  workingDays: number | null;
  daysPresent: number | null;
  overridden: boolean;
}

/**
 * The attendance a card prints for these (saved or edited) values, worked out as
 * pdf/builder.py _attendance() does: a day-count override recomputes the % from the
 * final counts unless the % is overridden too; a % override alone hides the days.
 */
function cardAttendance(d: Draft, row: PdfStudentRosterRow): CardAttendance {
  // The card ignores the computed counts of a student with no working days.
  const computedWd = row.computed_working_days || null;
  const computedDp = computedWd != null ? row.computed_days_present : null;
  const wdOverride = parseNumber(d.workingDays);
  const dpOverride = parseNumber(d.daysPresent);
  const pctOverride = parseNumber(d.attendancePct);
  if (wdOverride != null || dpOverride != null) {
    const workingDays = wdOverride ?? computedWd;
    const daysPresent = dpOverride ?? computedDp;
    const pct =
      pctOverride ?? (workingDays && daysPresent != null ? roundTenth((daysPresent / workingDays) * 100) : null);
    return { pct, workingDays, daysPresent, overridden: true };
  }
  if (pctOverride != null) return { pct: pctOverride, workingDays: null, daysPresent: null, overridden: true };
  return { pct: row.computed_attendance_pct, workingDays: computedWd, daysPresent: computedDp, overridden: false };
}

/** True when the card would print more days present than working days (it refuses to print). */
function daysOverWorking(d: Draft, row: PdfStudentRosterRow): boolean {
  // Checked on what the card prints, so a single overridden count is compared with the computed other one.
  const { workingDays, daysPresent } = cardAttendance(d, row);
  return workingDays != null && daysPresent != null && daysPresent > workingDays;
}

/**
 * What stops a pending row from saving. The day counts are held to the computed ones only
 * when this edit changes them (an admin's override), as the server does: a count saved
 * earlier can drift past the computed one as attendance is marked, and that mustn't block
 * a teacher's remark or house.
 */
function problemsOf(d: Draft, row: PdfStudentRosterRow, daysEdited: boolean): Problem[] {
  const out: Problem[] = [];
  // Saving would send remarks: null and silently drop the Punjabi text.
  if (!d.remarksEn.trim() && d.remarksPa.trim()) out.push("englishRemarkMissing");
  if (daysEdited && daysOverWorking(d, row)) out.push("daysPresentOverWorkingDays");
  return out;
}

/**
 * Drop edit fields that equal the saved value (they change nothing). Run when the
 * saved values change, so a save clears its own edits in the same render that
 * shows the new values; anything typed while the save was in flight stays pending.
 * Returns `prev` itself when nothing matches, so it never re-renders for nothing.
 */
function dropSavedEdits(prev: Edits, baseline: Map<number, Draft>): Edits {
  let changed = false;
  const next: Edits = {};
  for (const [id, edit] of Object.entries(prev)) {
    const base = baseline.get(Number(id)) ?? EMPTY_DRAFT;
    const kept: Partial<Draft> = {};
    for (const key of Object.keys(edit) as DraftKey[]) {
      if (edit[key] !== base[key]) kept[key] = edit[key];
      else changed = true;
    }
    if (Object.keys(kept).length) next[Number(id)] = kept;
    else changed = true;
  }
  return changed ? next : prev;
}

/** The list plus any saved value missing from it (e.g. a house name since retired). */
function withValues(list: string[], ...values: string[]): string[] {
  const out = [...list];
  for (const v of values) if (v && !out.includes(v)) out.push(v);
  return out;
}

/** Same shape as the server's pdf_filename(): report-card_<class>_<roll>_<name>. */
function cardFilename(className: string, row: PdfStudentRosterRow): string {
  const safe = (s: string) => s.replace(/[^A-Za-z0-9.-]+/g, "-").replace(/^-+|-+$/g, "") || "x";
  return `report-card_${safe(className)}${row.roll_no ? `_${safe(row.roll_no)}` : ""}_${safe(row.name)}`;
}

/**
 * The per-student side of one report-card template: what each card will print
 * (total, rank, attendance), remarks in English + Punjabi, house, admin
 * overrides, whether the stored PDF is current, and single / bulk generation.
 * Used on the Results page "Report cards" tab and on the template detail page.
 */
export function ReportCardRoster({ template }: { template: PdfTemplate }) {
  const { t } = useTranslation();
  if (template.kind !== "report-card") {
    return (
      <Card>
        <CardContent className="p-6 text-sm text-muted-foreground">
          {t("portal.reportCards.reportCardsOnly", "This view is for report-card templates.")}
        </CardContent>
      </Card>
    );
  }
  // Another template is another class or term: start from a clean slate.
  return <TemplateRoster key={template.id} template={template} />;
}

function TemplateRoster({ template }: { template: PdfTemplate }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { isAdmin, isSuperAdmin } = useAuth();
  const meta = useMeta();
  const { scopeLabel } = useReportCardLabels();
  const settings = (template.data ?? {}) as Partial<ReportCardTemplateData>;
  const tid = template.id;
  const rosterKey = ["pdf-roster", tid];
  const studentDataKey = ["pdf-student-data", tid];
  const jobsKey = ["pdf-render-jobs", tid];

  // ── Server state ──────────────────────────────────────────────────────
  const rosterQ = useQuery(templateRosterQuery(tid));
  // Marks saved or submitted anywhere change totals, ranks and which cards are current,
  // and so do the class's subjects and exams (a term, max marks or a rename).
  useSSE("marks-batches", [rosterKey]);
  useSSE("class-subjects", [rosterKey]);
  const dataQ = useQuery<PdfStudentDataRow[]>({
    queryKey: studentDataKey,
    queryFn: () => api.get<PdfStudentDataRow[]>(`/pdf/templates/${tid}/student-data`).then((r) => r.data),
    retry: (failures, e) => !isClientError(e) && failures < 1,
  });
  const students = useMemo(() => rosterQ.data?.students ?? [], [rosterQ.data]);

  // ── Edits: inputs show the saved values with local changes laid over them ──
  const baseline = useMemo(() => {
    const m = new Map<number, Draft>();
    for (const row of dataQ.data ?? []) m.set(row.student_id, toDraft(row.data as ReportCardStudentData));
    return m;
  }, [dataQ.data]);
  const [edits, setEdits] = useState<Edits>({});
  useEffect(() => setEdits((prev) => dropSavedEdits(prev, baseline)), [baseline]);
  const baseOf = (id: number): Draft => baseline.get(id) ?? EMPTY_DRAFT;
  const draftOf = (id: number): Draft => ({ ...baseOf(id), ...edits[id] });
  const setField = (id: number, key: DraftKey, value: string) =>
    setEdits((prev) => ({ ...prev, [id]: { ...prev[id], [key]: value } }));
  // Editing needs the saved values to diff against.
  const canEdit = dataQ.data !== undefined;

  const pending = useMemo(() => {
    const out: PendingRow[] = [];
    for (const s of students) {
      const edit = edits[s.id];
      if (!edit) continue;
      const base = baseline.get(s.id) ?? EMPTY_DRAFT;
      const draft = { ...base, ...edit };
      const data = buildPatch(base, draft, isAdmin);
      const daysEdited = "workingDays" in data || "daysPresent" in data;
      if (Object.keys(data).length) out.push({ id: s.id, data, problems: problemsOf(draft, s, daysEdited) });
    }
    return out;
  }, [students, edits, baseline, isAdmin]);
  const pendingById = useMemo(() => new Map(pending.map((p) => [p.id, p])), [pending]);
  // A row marked in red waits; it doesn't hold up saving the others.
  const savable = pending.filter((p) => p.problems.length === 0);
  const hasPending = pending.length > 0;

  // Reloading, a link to another page, or another class / scope / tab asks before dropping these edits.
  useUnsavedChanges(hasPending);

  const save = useMutation({
    mutationFn: (rows: PendingRow[]) =>
      api
        .put<PdfStudentDataRow[]>(`/pdf/templates/${tid}/student-data`, {
          entries: rows.map((r) => ({ student_id: r.id, data: r.data })),
        })
        .then((r) => r.data),
    onSuccess: (saved, rows) => {
      // The new saved values clear the matching edits (see dropSavedEdits).
      qc.setQueryData<PdfStudentDataRow[]>(studentDataKey, (old) => {
        const byId = new Map((old ?? []).map((r) => [r.student_id, r]));
        for (const r of saved) byId.set(r.student_id, r);
        return [...byId.values()];
      });
      qc.invalidateQueries({ queryKey: studentDataKey });
      qc.invalidateQueries({ queryKey: rosterKey }); // remarks and overrides change what a card prints
      toast(t("portal.reportCards.saved", "Saved changes for {{count}} students", { count: rows.length }), "success");
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  /**
   * Cards print what is saved, so pending edits are saved before any render. A row
   * marked in red holds up only a render that includes it (`ids` null = every student).
   */
  const saveFirst = async (ids: number[] | null): Promise<boolean> => {
    if (pending.some((p) => p.problems.length > 0 && (ids == null || ids.includes(p.id)))) {
      toast(t("portal.reportCards.fixRowsFirst", "Fix the rows marked in red first."), "warning");
      return false;
    }
    if (!savable.length) return true;
    try {
      await save.mutateAsync(savable);
      return true;
    } catch {
      return false; // save's onError already said why
    }
  };

  const discard = () => {
    if (window.confirm(t("portal.reportCards.discardConfirm", "Discard {{count}} unsaved changes?", { count: pending.length }))) {
      setEdits({});
    }
  };

  // ── Generation options ────────────────────────────────────────────────
  const [force, setForce] = useState(false);
  // Draft marks: the template's own setting until a super-admin picks otherwise here.
  // Saving the template (a new version) starts again from its setting.
  const templateDrafts = settings.includeDrafts === true;
  const [draftsPick, setDraftsPick] = useState<{ version: number; value: boolean } | null>(null);
  const includeDrafts = draftsPick?.version === template.version ? draftsPick.value : templateDrafts;
  const renderOptions = () => {
    const body: { force: boolean; include_drafts?: boolean } = { force: isAdmin && force };
    // A super-admin's choice is sent either way (the server refuses only `true` from anyone
    // else); without the key the server uses the template's setting.
    if (isSuperAdmin) body.include_drafts = includeDrafts;
    return body;
  };

  // ── Background runs ───────────────────────────────────────────────────
  const [jobId, setJobId] = useState<number | null>(null);
  const jobsQ = useQuery<RenderJob[]>({
    queryKey: jobsKey,
    queryFn: () => api.get<RenderJob[]>("/pdf/render-jobs", { params: { template_id: tid } }).then((r) => r.data),
    staleTime: 0,
    retry: false,
  });
  useEffect(() => {
    // A run already going (from before a reload, or started by a colleague): follow it.
    const newest = jobsQ.data?.[0];
    if (!newest || !isRenderJobActive(newest)) return;
    const key = renderJobQuery(newest.id).queryKey;
    if (!qc.getQueryData(key)) qc.setQueryData(key, newest);
    setJobId(newest.id);
  }, [jobsQ.data, qc]);
  // Reads the job RenderJobProgress polls, to know whether a run is still going.
  const jobQ = useQuery({ ...renderJobQuery(jobId ?? 0), enabled: false });
  // A run the server no longer answers for (4xx) doesn't hold up new ones.
  const jobRunning =
    jobId != null && !isClientError(jobQ.error) && (jobQ.data ? isRenderJobActive(jobQ.data) : !jobQ.isError);

  const attach = (job: RenderJob) => {
    qc.setQueryData(renderJobQuery(job.id).queryKey, job);
    setJobId(job.id);
    qc.invalidateQueries({ queryKey: jobsKey });
  };

  const attachToActiveRun = async (): Promise<boolean> => {
    try {
      const { data } = await api.get<RenderJob[]>("/pdf/render-jobs", { params: { template_id: tid } });
      const active = data.find((j) => isRenderJobActive(j));
      if (!active) return false;
      attach(active);
      toast(t("portal.reportCards.alreadyRunning", "Cards for this class are already being generated. Showing that run."), "warning");
      return true;
    } catch {
      return false;
    }
  };

  const startJob = useMutation({
    mutationFn: (studentIds: number[] | null) =>
      api
        .post<RenderJob>(`/pdf/templates/${tid}/render-jobs`, { student_ids: studentIds, ...renderOptions() })
        .then((r) => r.data),
    onSuccess: (job) => attach(job),
    onError: async (e) => {
      // 409: a run for this template is already active, so show that one instead.
      if (axios.isAxiosError(e) && e.response?.status === 409 && (await attachToActiveRun())) return;
      toast(apiError(e), "error");
    },
  });

  const generate = async (studentIds: number[] | null) => {
    if (await saveFirst(studentIds)) startJob.mutate(studentIds);
  };

  const onJobFinished = (job: RenderJob) => {
    qc.invalidateQueries({ queryKey: rosterKey });
    qc.invalidateQueries({ queryKey: jobsKey });
    if (job.status === "done") {
      const ready = job.results.filter((r) => r.status !== "error").length;
      toast(
        t("portal.reportCards.jobDoneToast", "{{ready}} of {{total}} report cards ready", { ready, total: job.total }),
        job.error_count ? "warning" : "success",
      );
    } else if (job.status === "failed") {
      toast(job.error || t("portal.reportCards.jobFailed", "Stopped with an error"), "error");
    }
  };

  // ── One card at a time (synchronous render) ───────────────────────────
  const [rendering, setRendering] = useState<ReadonlySet<number>>(() => new Set());
  const generateOne = async (row: PdfStudentRosterRow) => {
    if (!(await saveFirst([row.id]))) return;
    setRendering((s) => new Set(s).add(row.id));
    try {
      const { data } = await api.post<{ results: PdfRenderResultRow[] }>(
        `/pdf/templates/${tid}/render`,
        { student_ids: [row.id], ...renderOptions() },
        { timeout: SYNC_RENDER_TIMEOUT_MS },
      );
      const result = data.results.find((r) => r.student_id === row.id);
      if (!result || result.status === "error") {
        toast(result?.error || t("portal.reportCards.generateFailed", "The report card couldn't be generated."), "error");
      } else {
        const ready = t("portal.reportCards.cardReady", "Report card ready for {{name}}", { name: row.name });
        const warnings = result.warnings ?? [];
        toast(warnings.length ? `${ready} · ${warnings.join(" · ")}` : ready, warnings.length ? "warning" : "success");
      }
    } catch (e) {
      toast(apiError(e), "error");
    } finally {
      setRendering((s) => {
        const next = new Set(s);
        next.delete(row.id);
        return next;
      });
      qc.invalidateQueries({ queryKey: rosterKey });
    }
  };

  // ── Selection ─────────────────────────────────────────────────────────
  const [selected, setSelected] = useState<ReadonlySet<number>>(() => new Set());
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

  // ── Admin overrides ───────────────────────────────────────────────────
  const [showOverrides, setShowOverrides] = useState(false);
  // What an empty override prints: the roster carries the computed values from the card's own engine,
  // and an empty attendance % is worked out from the day counts being typed.
  const computedPlaceholder = (row: PdfStudentRosterRow, draft: Draft, key: OverrideNumberKey): string => {
    const value =
      key === "rank" ? row.computed_rank
      : key === "classSize" ? rosterQ.data?.class_size
      : key === "attendancePct" ? cardAttendance({ ...draft, attendancePct: "" }, row).pct
      : key === "workingDays" ? row.computed_working_days
      : row.computed_days_present;
    return value != null ? formatNumber(value) : "—";
  };
  const hasOverride = (d: Draft) => d.promotion !== "" || OVERRIDE_KEYS.some((k) => d[k] !== "");
  const clearOverrides = (id: number) =>
    setEdits((prev) => ({
      ...prev,
      [id]: { ...prev[id], rank: "", classSize: "", attendancePct: "", workingDays: "", daysPresent: "", promotion: "" },
    }));

  // ── Labels ────────────────────────────────────────────────────────────
  const overrideLabel: Record<OverrideNumberKey, string> = {
    rank: t("portal.results.rank", "Rank"),
    classSize: t("portal.reportCards.classSize", "Class size"),
    attendancePct: t("portal.reportCards.attendancePct", "Attendance %"),
    workingDays: t("portal.reportCards.workingDays", "Working days"),
    daysPresent: t("portal.reportCards.daysPresent", "Days present"),
  };
  const promotionNames: Record<string, string> = {
    Promoted: t("portal.reportCards.promoted", "Promoted"),
    Conditional: t("portal.reportCards.conditional", "Conditional"),
    Detained: t("portal.reportCards.detained", "Detained"),
  };
  const problemText = (problem: Problem, draft: Draft, row: PdfStudentRosterRow): string => {
    if (problem === "englishRemarkMissing") {
      return t("portal.reportCards.englishRemarkMissing", "Add the English remark too; the Punjabi line prints under it.");
    }
    // One of the two may be the computed count, so say both.
    const { workingDays, daysPresent } = cardAttendance(draft, row);
    return t("portal.reportCards.daysPresentTooHigh", "Days present ({{present}}) can't be more than working days ({{working}}).", {
      present: formatNumber(daysPresent),
      working: formatNumber(workingDays),
    });
  };
  // The per-row preview renders what is saved, with the template's draft-marks setting.
  const previewSaveFirst = t("portal.reportCards.previewSaveFirst", "Save this row's changes first: the preview shows what is saved.");
  const previewDraftsNote =
    includeDrafts !== templateDrafts
      ? t(
          "portal.reportCards.previewTemplateDrafts",
          "The preview follows the card settings for draft marks, not the “Include draft marks” choice here.",
        )
      : null;
  const overriddenMark = (text: string, overridden: boolean) =>
    overridden ? (
      <span className="underline decoration-dotted underline-offset-4" title={t("portal.reportCards.overriddenHint", "Set by hand (override)")}>
        {text}
        <span className="sr-only"> ({t("portal.reportCards.overridden", "override")})</span>
      </span>
    ) : (
      text
    );
  const statusBadge = (row: PdfStudentRosterRow) => {
    const cls = "whitespace-nowrap";
    if (rendering.has(row.id)) {
      return (
        <Badge variant="info" className={cn(cls, "gap-1")}>
          <Spinner className="h-3 w-3" /> {t("portal.reportCards.generating", "Generating…")}
        </Badge>
      );
    }
    if (row.cached_pdf_id != null) return <Badge variant="success" className={cls}>{t("portal.reportCards.fresh", "Ready")}</Badge>;
    // An error beats "needs update": generating again won't work until it is fixed.
    if (row.error) return <Badge variant="destructive" className={cls}>{t("portal.reportCards.cantGenerate", "Can't generate")}</Badge>;
    if (row.stale_pdf_id != null) return <Badge variant="warning" className={cls}>{t("portal.reportCards.stale", "Needs update")}</Badge>;
    return <Badge variant="secondary" className={cls}>{t("portal.reportCards.notGenerated", "Not generated")}</Badge>;
  };

  const busy = jobRunning || startJob.isPending || save.isPending;

  // ── Loading / error ───────────────────────────────────────────────────
  if (!rosterQ.data) {
    if (rosterQ.isError) {
      return (
        <Card>
          <CardContent className="space-y-3 p-6">
            <div role="alert" className="flex items-start gap-2 rounded-lg bg-destructive/10 p-4 text-sm text-destructive">
              <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0" />
              <div>
                <p className="font-medium">{t("portal.reportCards.loadError", "Couldn't load the report cards for this class.")}</p>
                <p>{apiError(rosterQ.error)}</p>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={() => void rosterQ.refetch()}>
              {t("portal.common.tryAgain", "Try again")}
            </Button>
          </CardContent>
        </Card>
      );
    }
    return (
      <Card>
        <CardContent className="flex items-center gap-2 p-6 text-sm text-muted-foreground">
          <Spinner /> {t("portal.reportCards.loading", "Loading report cards…")}
        </CardContent>
      </Card>
    );
  }
  const roster = rosterQ.data;

  return (
    <Card>
      <CardHeader className="space-y-3 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="space-y-1.5">
            <CardTitle>{t("portal.reportCards.title", "Report cards")}</CardTitle>
            <CardDescription>
              {template.class_name} · {scopeLabel(template.scope ?? roster.scope)} · {template.session} ·{" "}
              {t("portal.reportCards.studentCount", "{{count}} students", { count: students.length })}
            </CardDescription>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {hasPending && (
              <Button variant="ghost" size="sm" onClick={discard} disabled={save.isPending}>
                <Undo2 /> {t("portal.reportCards.discard", "Discard")}
              </Button>
            )}
            <Button size="sm" onClick={() => save.mutate(savable)} disabled={!savable.length || save.isPending}>
              {save.isPending ? <Spinner /> : <Save />}
              {hasPending
                ? t("portal.reportCards.saveChanges", "Save changes ({{count}})", { count: savable.length })
                : t("portal.reportCards.allSaved", "All changes saved")}
            </Button>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t pt-3">
          {isAdmin && (
            <Button
              variant={showOverrides ? "secondary" : "outline"}
              size="sm"
              aria-pressed={showOverrides}
              onClick={() => setShowOverrides((v) => !v)}
            >
              <SlidersHorizontal /> {t("portal.reportCards.override", "Overrides")}
            </Button>
          )}
          {isAdmin && (
            <label className="flex cursor-pointer items-center gap-2 text-sm">
              <Checkbox checked={force} onCheckedChange={(v) => setForce(v === true)} />
              {t("portal.reportCards.force", "Force re-render")}
            </label>
          )}
          {isSuperAdmin && (
            <label
              className="flex cursor-pointer items-center gap-2 text-sm"
              title={
                templateDrafts
                  ? t(
                      "portal.reportCards.includeDraftsHintOn",
                      "This template's card settings print draft marks. Untick to leave them off; those cards then show as “Needs update”.",
                    )
                  : t(
                      "portal.reportCards.includeDraftsHintOff",
                      "This template's card settings leave draft marks off. Tick to print them; those cards then show as “Needs update”.",
                    )
              }
            >
              <Checkbox
                checked={includeDrafts}
                onCheckedChange={(v) => setDraftsPick({ version: template.version, value: v === true })}
              />
              {t("portal.reportCards.includeDrafts", "Include draft marks")}
            </label>
          )}
          <div className="flex flex-wrap gap-2 sm:ml-auto">
            <Button variant="outline" size="sm" disabled={!selectedIds.length || busy} onClick={() => void generate(selectedIds)}>
              <RefreshCw /> {t("portal.reportCards.generate", "Generate selected")}
              {selectedIds.length ? ` (${selectedIds.length})` : ""}
            </Button>
            <Button size="sm" disabled={!students.length || busy} onClick={() => void generate(null)}>
              {startJob.isPending ? <Spinner /> : <Layers />} {t("portal.reportCards.generateAll", "Generate all")}
            </Button>
          </div>
        </div>
      </CardHeader>

      <CardContent className="space-y-3">
        {jobId != null && (
          <RenderJobProgress
            key={jobId}
            jobId={jobId}
            onFinished={onJobFinished}
            roster={students}
            rosterUpdatedAt={rosterQ.dataUpdatedAt}
          />
        )}

        {rosterQ.isError && (
          <div role="alert" className="flex flex-wrap items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            <TriangleAlert className="h-4 w-4 shrink-0" />
            <span>{t("portal.reportCards.refreshError", "Couldn't refresh the card list.")} {apiError(rosterQ.error)}</span>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => void rosterQ.refetch()}>
              {t("portal.common.tryAgain", "Try again")}
            </Button>
          </div>
        )}
        {dataQ.isError && !dataQ.data && (
          <div role="alert" className="flex flex-wrap items-center gap-2 rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
            <TriangleAlert className="h-4 w-4 shrink-0" />
            <span>
              {t("portal.reportCards.dataLoadError", "Couldn't load the saved remarks and houses, so editing is paused.")} {apiError(dataQ.error)}
            </span>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => void dataQ.refetch()}>
              {t("portal.common.tryAgain", "Try again")}
            </Button>
          </div>
        )}

        {roster.warnings.length > 0 && (
          <div role="status" className="flex items-start gap-2 rounded-md border border-amber-300 bg-amber-50 p-3 text-sm text-amber-900">
            <TriangleAlert className="mt-0.5 h-4 w-4 shrink-0 text-amber-700" />
            <ul className="space-y-0.5">
              {roster.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        )}

        {students.length === 0 ? (
          <p className="py-8 text-center text-sm text-muted-foreground">
            {t("portal.reportCards.noStudents", "No active students in {{cls}}.", { cls: template.class_name })}
          </p>
        ) : (
          <>
            <div className="flex flex-wrap gap-x-5 gap-y-1.5 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1.5">
                <Badge variant="success">{t("portal.reportCards.fresh", "Ready")}</Badge>
                {t("portal.reportCards.legendFresh", "matches the current marks and remarks")}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Badge variant="warning">{t("portal.reportCards.stale", "Needs update")}</Badge>
                {t("portal.reportCards.legendStale", "something changed after the card was made; generate it again")}
              </span>
              <span className="inline-flex items-center gap-1.5">
                <Badge variant="outline" className="border-amber-300 text-amber-800">{t("portal.reportCards.provisional", "Provisional")}</Badge>
                {t("portal.reportCards.legendProvisional", "some marks are missing or still drafts, so totals and rank can still change")}
              </span>
            </div>

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
                  <TableHead>{t("portal.results.roll", "Roll")}</TableHead>
                  <TableHead>{t("portal.results.student", "Student")}</TableHead>
                  <TableHead className="text-right">{t("portal.results.total", "Total")}</TableHead>
                  <TableHead className="text-right">{t("portal.results.rank", "Rank")}</TableHead>
                  <TableHead className="text-right">{t("portal.results.attendance", "Att %")}</TableHead>
                  <TableHead>{t("portal.reportCards.house", "House")}</TableHead>
                  <TableHead>{t("portal.reportCards.remarksEn", "Remarks (English)")}</TableHead>
                  <TableHead>{t("portal.reportCards.remarksPa", "Remarks (Punjabi)")}</TableHead>
                  <TableHead>{t("portal.reportCards.card", "Card")}</TableHead>
                  <TableHead className="text-right">{t("portal.common.actions", "Actions")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {students.map((row) => {
                  const base = baseOf(row.id);
                  const draft = draftOf(row.id);
                  const problems = pendingById.get(row.id)?.problems ?? [];
                  const pdfId = row.cached_pdf_id ?? row.stale_pdf_id;
                  const isRendering = rendering.has(row.id);
                  // "Ready" is worked out with the template's draft-marks setting: another choice
                  // here prints a different card, so it isn't up to date for that render.
                  const upToDate = row.cached_pdf_id != null && !(isAdmin && force) && includeDrafts === templateDrafts;
                  const previewNote = pendingById.has(row.id) ? previewSaveFirst : previewDraftsNote;
                  const classSize = parseNumber(base.classSize) ?? roster.class_size;
                  // What the card prints; until the saved overrides load, the roster's own figure.
                  const attendance = canEdit
                    ? cardAttendance(base, row)
                    : { pct: row.attendance_pct, overridden: row.overrides.includes("attendancePct") };
                  const englishMissing = problems.includes("englishRemarkMissing");
                  const daysProblem = problems.includes("daysPresentOverWorkingDays");
                  return (
                    <Fragment key={row.id}>
                      <TableRow
                        data-state={selected.has(row.id) ? "selected" : undefined}
                        className={cn(pendingById.has(row.id) && "bg-vasant-cream/40")}
                      >
                        <TableCell>
                          <Checkbox
                            checked={selected.has(row.id)}
                            onCheckedChange={() => toggleOne(row.id)}
                            aria-label={t("portal.reportCards.selectStudent", "Select {{name}}", { name: row.name })}
                          />
                        </TableCell>
                        <TableCell className="tabular-nums text-muted-foreground">{row.roll_no || "—"}</TableCell>
                        <TableCell className="min-w-[12rem]">
                          <div className="font-medium">{row.name}</div>
                          {(pendingById.has(row.id) || row.provisional || row.draft_marks > 0 || row.missing_dob) && (
                            <div className="mt-1 flex flex-wrap gap-1">
                              {/* Says which rows Save and Discard act on; the row tint alone is easy to miss. */}
                              {pendingById.has(row.id) && (
                                <Badge variant="warning">{t("portal.templates.unsaved", "Unsaved changes")}</Badge>
                              )}
                              {row.provisional && (
                                <Badge variant="outline" className="border-amber-300 text-amber-800">
                                  {t("portal.reportCards.provisional", "Provisional")}
                                </Badge>
                              )}
                              {row.draft_marks > 0 && (
                                <Badge
                                  variant="outline"
                                  title={t("portal.reportCards.draftsHint", "{{count}} marks are still drafts and stay off the card", { count: row.draft_marks })}
                                >
                                  {t("portal.reportCards.drafts", "Drafts")}
                                </Badge>
                              )}
                              {row.missing_dob && (
                                <Badge variant="outline" className="text-muted-foreground">
                                  {t("portal.reportCards.missingDob", "DOB missing")}
                                </Badge>
                              )}
                            </div>
                          )}
                          {row.error && <p className="mt-1 text-xs text-destructive">{row.error}</p>}
                          {problems.map((p) => (
                            <p key={p} className="mt-1 text-xs text-destructive">{problemText(p, draft, row)}</p>
                          ))}
                          {!isAdmin && canEdit && daysOverWorking(draft, row) && (
                            // Only admins can change the override; a teacher's remarks still save.
                            <p className="mt-1 text-xs text-amber-800">
                              {t(
                                "portal.reportCards.attendanceNeedsAdmin",
                                "An admin needs to correct this student's attendance override before the card can print.",
                              )}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-right tabular-nums">
                          {row.has_marks && row.total != null ? (
                            <>
                              <div>
                                {formatNumber(row.total)} <span className="text-muted-foreground">/ {formatNumber(row.max)}</span>
                              </div>
                              <div className="text-xs text-muted-foreground">
                                {/* Two decimals, as the card prints it: one would show 90.95 as 91, past its grade's band. */}
                                {row.percentage != null ? `${formatNumber(row.percentage, 2)}%` : "—"}
                              </div>
                            </>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-right tabular-nums">
                          {row.rank != null ? (
                            <>
                              {overriddenMark(formatNumber(row.rank), base.rank !== "")}
                              <span className="text-muted-foreground"> / {formatNumber(classSize)}</span>
                            </>
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="whitespace-nowrap text-right tabular-nums">
                          {attendance.pct != null ? (
                            overriddenMark(`${formatNumber(attendance.pct)}%`, attendance.overridden)
                          ) : (
                            <span className="text-muted-foreground">—</span>
                          )}
                        </TableCell>
                        <TableCell className="min-w-[9rem]">
                          <Select
                            value={draft.house || NO_HOUSE}
                            onValueChange={(v) => setField(row.id, "house", v === NO_HOUSE ? "" : v)}
                            disabled={!canEdit}
                          >
                            <SelectTrigger className="h-8" aria-label={`${t("portal.reportCards.house", "House")} · ${row.name}`}>
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value={NO_HOUSE}>—</SelectItem>
                              {withValues(meta.houses, draft.house, base.house).map((h) => (
                                <SelectItem key={h} value={h}>{h}</SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                          {!draft.house && !base.house && row.house && (
                            <p className="mt-1 text-[11px] text-muted-foreground">
                              {t("portal.reportCards.houseFromOtherTerm", "Prints {{house}} (set in another term)", { house: row.house })}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="min-w-[13rem]">
                          <Input
                            className={cn("h-8", englishMissing && "border-destructive focus-visible:ring-destructive")}
                            maxLength={REMARK_MAX}
                            value={draft.remarksEn}
                            onChange={(e) => setField(row.id, "remarksEn", e.target.value)}
                            placeholder={
                              settings.remarksDefault?.en
                                ? t("portal.reportCards.defaultRemark", "Default: {{text}}", { text: settings.remarksDefault.en })
                                : undefined
                            }
                            aria-label={`${t("portal.reportCards.remarksEn", "Remarks (English)")} · ${row.name}`}
                            aria-invalid={englishMissing || undefined}
                            disabled={!canEdit}
                          />
                        </TableCell>
                        <TableCell className="min-w-[13rem]">
                          <Input
                            lang="pa"
                            className="h-8 font-gurmukhi"
                            maxLength={REMARK_MAX}
                            value={draft.remarksPa}
                            onChange={(e) => setField(row.id, "remarksPa", e.target.value)}
                            placeholder={settings.remarksDefault?.pa || undefined}
                            aria-label={`${t("portal.reportCards.remarksPa", "Remarks (Punjabi)")} · ${row.name}`}
                            disabled={!canEdit}
                          />
                        </TableCell>
                        <TableCell>{statusBadge(row)}</TableCell>
                        <TableCell className="whitespace-nowrap text-right">
                          <div className="flex items-center justify-end gap-1">
                            {isAdmin && (
                              <Button
                                size="icon"
                                variant="ghost"
                                className="h-8 w-8"
                                disabled={!!row.error}
                                onClick={() => {
                                  // Say so rather than show the old remark (a save first would get the tab blocked).
                                  if (pendingById.has(row.id)) toast(previewSaveFirst, "warning");
                                  else void openReportCardPreview(tid, row.id);
                                }}
                                title={
                                  previewNote
                                    ? `${t("portal.reportCards.preview", "Preview")} · ${previewNote}`
                                    : t("portal.reportCards.preview", "Preview")
                                }
                                aria-label={`${t("portal.reportCards.preview", "Preview")} · ${row.name}`}
                              >
                                <Eye />
                              </Button>
                            )}
                            <Button
                              size="icon"
                              variant="ghost"
                              className="h-8 w-8"
                              disabled={pdfId == null}
                              onClick={() => {
                                if (pdfId != null) downloadCachedPdf(pdfId, cardFilename(template.class_name, row));
                              }}
                              title={
                                row.cached_pdf_id == null && row.stale_pdf_id != null
                                  ? t("portal.reportCards.downloadOutdated", "Download the outdated card")
                                  : t("portal.reportCards.download", "Download")
                              }
                              aria-label={`${t("portal.reportCards.download", "Download")} · ${row.name}`}
                            >
                              <Download />
                            </Button>
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-8"
                              disabled={!!row.error || isRendering || jobRunning || upToDate}
                              onClick={() => void generateOne(row)}
                              title={upToDate ? t("portal.reportCards.upToDate", "Already up to date") : undefined}
                            >
                              {isRendering ? <Spinner /> : <RefreshCw />} {t("portal.reportCards.generateOne", "Generate")}
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>

                      {isAdmin && showOverrides && (
                        <TableRow className="bg-muted/30 hover:bg-muted/30">
                          <TableCell />
                          <TableCell colSpan={COLUMNS - 1} className="pt-1">
                            <div className="flex flex-wrap items-end gap-3">
                              {OVERRIDE_FIELDS.map((f) => (
                                <label key={f.key} className="space-y-1">
                                  <span className="block text-[11px] font-medium text-muted-foreground">{overrideLabel[f.key]}</span>
                                  <NumberField
                                    className="h-8 w-24"
                                    value={draft[f.key]}
                                    min={f.min}
                                    max={f.max}
                                    inputMode={f.integer ? "numeric" : "decimal"}
                                    placeholder={computedPlaceholder(row, draft, f.key)}
                                    invalid={
                                      daysProblem && (f.key === "daysPresent" || f.key === "workingDays") && draft[f.key] !== ""
                                    }
                                    aria-label={`${overrideLabel[f.key]} · ${row.name}`}
                                    disabled={!canEdit}
                                    onChange={(v) => {
                                      // Never negative; whole numbers where the card needs them.
                                      if (v.includes("-") || (f.integer && v.includes("."))) return;
                                      setField(row.id, f.key, v);
                                    }}
                                  />
                                </label>
                              ))}
                              <div className="space-y-1">
                                <span className="block text-[11px] font-medium text-muted-foreground">
                                  {t("portal.reportCards.promotion", "Promotion")}
                                </span>
                                <Select
                                  value={draft.promotion || AUTO_PROMOTION}
                                  onValueChange={(v) => setField(row.id, "promotion", v === AUTO_PROMOTION ? "" : v)}
                                  disabled={!canEdit}
                                >
                                  <SelectTrigger className="h-8 w-40" aria-label={`${t("portal.reportCards.promotion", "Promotion")} · ${row.name}`}>
                                    <SelectValue />
                                  </SelectTrigger>
                                  <SelectContent>
                                    <SelectItem value={AUTO_PROMOTION}>{t("portal.reportCards.automatic", "Automatic")}</SelectItem>
                                    {withValues(meta.promotion_values, draft.promotion, base.promotion).map((p) => (
                                      <SelectItem key={p} value={p}>{promotionNames[p] ?? p}</SelectItem>
                                    ))}
                                  </SelectContent>
                                </Select>
                              </div>
                              {hasOverride(draft) && (
                                <Button variant="ghost" size="sm" className="h-8" onClick={() => clearOverrides(row.id)} disabled={!canEdit}>
                                  {t("portal.reportCards.clearOverrides", "Clear overrides")}
                                </Button>
                              )}
                            </div>
                          </TableCell>
                        </TableRow>
                      )}
                    </Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </>
        )}
      </CardContent>
    </Card>
  );
}
