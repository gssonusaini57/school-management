import { useMemo, useRef, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { FileSpreadsheet, AlertTriangle, BookOpen, Lock, Send, Save, FilePen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { NumberField } from "@/components/ui/number-field";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { useSSE } from "@/lib/sse";
import { CLASSES } from "@/lib/utils";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { MARKS_TEMPLATE } from "@/lib/templates";
import { SessionSelect } from "@/components/SessionSelect";
import { useCurrentSessionName } from "@/lib/session";
import { useMeta } from "@/lib/meta";
import { confirmLeave, useUnsavedChanges } from "@/lib/unsaved";
import type { Student, ClassSubject, ClassSubjectDetail, MarksBatchDetail } from "@/types/api";
import { useTranslation } from "react-i18next";

const fmtTs = (v: string | null): string => {
  if (!v) return "—";
  try { return new Date(v).toLocaleString(); } catch { return v; }
};

/** A typed mark as a number; null when blank or not a number (a lone "."), so it is never sent. */
const markNumber = (v: string): number | null => {
  const s = v.trim();
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
};

/** What a batch's rows put in the inputs: a mark, or a letter for a graded test. */
const itemsToInputs = (b: MarksBatchDetail | null, graded: boolean): Record<number, string> => {
  const out: Record<number, string> = {};
  for (const row of b?.items ?? []) out[row.student_id] = graded ? (row.grade ?? "") : String(row.marks);
  return out;
};

/** One saved state of a test's batch ("none" = no saved marks yet). Older servers send no revision. */
const revisionKey = (b: MarksBatchDetail | null): string =>
  b ? `${b.id}:${b.revision ?? b.updated_at}` : "none";

/** True when the inputs differ from what was loaded (blank and missing count as the same). */
const differs = (a: Record<number, string>, b: Record<number, string>): boolean =>
  Array.from(new Set([...Object.keys(a), ...Object.keys(b)])).some(
    (k) => (a[Number(k)] ?? "") !== (b[Number(k)] ?? ""),
  );

/** The test whose marks the inputs show, and the saved batch they were loaded from. */
interface Shown { test: string; rev: string | null; batchId: number | null; revision: number | null }
const NOTHING_SHOWN: Shown = { test: "", rev: null, batchId: null, revision: null };

/** A save's test (testKey) and its batch query, as they were when Save was clicked. */
interface SaveVars { test: string; key: readonly unknown[] }

export default function MarksEntry() {
  const { t } = useTranslation();
  const { user, isAdmin, isSuperAdmin } = useAuth();
  // Super-admin and admin see every class; staff are limited to their allowed list (none until assigned).
  const allowed = isAdmin ? CLASSES : user?.allowed_classes ?? [];

  const [cls, setCls] = useState("");
  const [subjectId, setSubjectId] = useState<string>("");
  const [componentId, setComponentId] = useState<string>("");
  // Empty until the user picks one; until then follow the server's current session.
  const [sessionPick, setSession] = useState("");
  const currentSession = useCurrentSessionName();
  const session = sessionPick || currentSession;
  const [marks, setMarks] = useState<Record<number, string>>({});
  const [importOpen, setImportOpen] = useState(false);
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);
  const [requestEditOpen, setRequestEditOpen] = useState(false);
  const [editReason, setEditReason] = useState("");
  // Set when the server refused a save because its marks changed after this
  // screen loaded them (or the batch got locked). Saving waits for a reload.
  const [staleError, setStaleError] = useState<string | null>(null);
  // The marks as loaded from the server; the inputs differ from it while edits are unsaved.
  const [baseline, setBaseline] = useState<Record<number, string>>({});
  const shown = useRef<Shown>(NOTHING_SHOWN);
  const qc = useQueryClient();
  const { grade_letters: gradeLetters } = useMeta();

  // ── Master-data queries ────────────────────────────────────────
  const subjectsQ = useQuery<ClassSubject[]>({
    queryKey: ["class-subjects", cls],
    queryFn: () => api.get("/class-subjects", { params: { class: cls } }).then((r) => r.data),
    enabled: !!cls,
  });

  const subjectDetailQ = useQuery<ClassSubjectDetail>({
    queryKey: ["class-subjects", "detail", subjectId],
    queryFn: () => api.get(`/class-subjects/${subjectId}`).then((r) => r.data),
    enabled: !!subjectId,
  });

  const studentsQ = useQuery<Student[]>({
    queryKey: ["students", cls],
    queryFn: () => api.get("/students", { params: { class: cls, page_size: 500 } }).then((r) => r.data.items),
    enabled: !!cls,
  });

  // Every subject: graded ones (Computer, P.E., …) take a letter per student.
  const eligibleSubjects = useMemo(() => subjectsQ.data ?? [], [subjectsQ.data]);

  const selectedSubject = useMemo(
    () => eligibleSubjects.find((s) => String(s.id) === subjectId) ?? null,
    [eligibleSubjects, subjectId],
  );

  const components = useMemo(
    () => (subjectDetailQ.data?.components ?? []).slice().sort((a, b) => a.order_index - b.order_index),
    [subjectDetailQ.data],
  );

  const selectedComponent = useMemo(
    () => components.find((c) => String(c.id) === componentId) ?? null,
    [components, componentId],
  );

  const maxMarks = selectedComponent?.max_marks ?? 0;
  // Max 0 = a graded exam component ("Term 1 Grade"): teachers pick a letter.
  const isGraded = !!selectedComponent && maxMarks === 0;

  // ── Batch query (the load-existing-marks side) ─────────────────
  const batchEnabled = !!cls && !!selectedSubject && !!selectedComponent && !!session;
  const batchKey = ["marks-batch", cls, selectedSubject?.subject_name, selectedComponent?.component_name, session];
  const batchQ = useQuery<MarksBatchDetail | null>({
    queryKey: batchKey,
    queryFn: () => api.get("/marks/batches", {
      params: {
        class: cls,
        subject: selectedSubject!.subject_name,
        exam_type: selectedComponent!.component_name,
        session,
      },
    }).then((r) => r.data),
    enabled: batchEnabled,
  });
  useSSE("marks-batches", [["marks-batch"]]);

  const batch = batchQ.data ?? null;
  // Editing waits until this test's saved marks have loaded. Saving from an
  // unfinished or failed load would send the wrong set, and the server
  // removes students missing from a save.
  const batchLoaded = batchEnabled && batchQ.isSuccess;
  const isLocked = batch?.status === "submitted";
  const isLockedForMe = isLocked && !isSuperAdmin;
  const hasPendingRequest = !!batch?.pending_edit_request_id;

  // Reset child selectors when parents change.
  useEffect(() => { setSubjectId(""); setComponentId(""); }, [cls]);
  useEffect(() => { setComponentId(""); }, [subjectId]);

  // The test the inputs belong to: "" until class, subject, exam and session are all picked.
  const testKey = batchEnabled
    ? JSON.stringify([cls, selectedSubject!.subject_name, selectedComponent!.component_name, session, isGraded])
    : "";
  const testKeyRef = useRef(testKey);
  testKeyRef.current = testKey;
  const dirty = differs(marks, baseline);
  // Leaving the page or reloading it (also the automatic reload after a deploy) asks first.
  useUnsavedChanges(dirty);

  /** Put a saved batch (or none) in the inputs, as the state edits are measured against. */
  const showBatch = (b: MarksBatchDetail | null) => {
    const next = itemsToInputs(b, isGraded);
    shown.current = { test: testKey, rev: revisionKey(b), batchId: b?.id ?? null, revision: b?.revision ?? null };
    setMarks(next);
    setBaseline(next);
    setStaleError(null);
  };

  // Another test (class, subject, exam or session): drop the last one's marks until this one loads.
  // (Declared before the load effect below, so a cached batch still wins.)
  useEffect(() => {
    shown.current = NOTHING_SHOWN;
    setMarks({});
    setBaseline({});
    setStaleError(null);
  }, [testKey]);

  // Picking another test drops the typed marks, so ask first while they aren't saved.
  const pick = (current: string, set: (v: string) => void) => (v: string) => {
    if (v !== current && confirmLeave()) set(v);
  };

  // ── Student sort: roll-first ───────────────────────────────────
  const sortedStudents = useMemo(() => {
    return (studentsQ.data ?? []).slice().sort((a, b) => {
      const ar = a.roll_no ?? "";
      const br = b.roll_no ?? "";
      if (ar !== "" || br !== "") {
        if (ar === "") return 1;
        if (br === "") return -1;
        const an = Number(ar);
        const bn = Number(br);
        if (!Number.isNaN(an) && !Number.isNaN(bn) && an !== bn) return an - bn;
        if (Number.isNaN(an) || Number.isNaN(bn)) {
          const c = ar.localeCompare(br);
          if (c !== 0) return c;
        }
      }
      return a.name.localeCompare(b.name);
    });
  }, [studentsQ.data]);

  // ── Mutations ──────────────────────────────────────────────────
  const buildPayload = () => ({
    class_name: cls,
    subject: selectedSubject!.subject_name,
    exam_type: selectedComponent!.component_name,
    session,
    max_marks: maxMarks,
    // The batch the inputs were loaded from (null = none) and its revision. The server
    // refuses the save (409) if the test's batch is another one or has changed since.
    base_batch_id: shown.current.batchId,
    base_revision: shown.current.revision,
    items: Object.entries(marks)
      .filter(([, v]) => (isGraded ? v !== "" : markNumber(v) != null))
      .map(([id, v]) => (isGraded ? { student_id: Number(id), grade: v } : { student_id: Number(id), marks: markNumber(v)! })),
  });

  const refetchBatch = () => qc.invalidateQueries({ queryKey: batchKey });

  // After this screen's own save: show what the server stored, with its new revision,
  // so the refetch that follows doesn't read as a change made elsewhere.
  const adopt = (vars: SaveVars, saved: MarksBatchDetail) => {
    qc.setQueryData(vars.key, saved);
    if (vars.test === testKeyRef.current) showBatch(saved);
    qc.invalidateQueries({ queryKey: vars.key });
  };

  const onSaveError = (e: unknown) => {
    toast(apiError(e), "error");
    if (axios.isAxiosError(e) && e.response?.status === 409) setStaleError(apiError(e));
  };

  const saveDraft = useMutation({
    mutationFn: (_vars: SaveVars) => api.post<MarksBatchDetail>("/marks/batches", buildPayload()).then((r) => r.data),
    onSuccess: (saved, vars) => {
      toast(
        isLocked
          ? t("portal.marksEntry.savedLocked", "Changes saved (marks stay submitted)")
          : t("portal.marksEntry.draftSaved", "Draft saved"),
        "success",
      );
      adopt(vars, saved);
    },
    onError: (e) => onSaveError(e),
  });

  const submitFinal = useMutation({
    mutationFn: async (vars: SaveVars) => {
      // Save then submit, so the latest unsaved edits land before lock.
      const saved = (await api.post<MarksBatchDetail>("/marks/batches", buildPayload())).data;
      adopt(vars, saved); // the save stands even if the submit fails
      return (await api.post<MarksBatchDetail>(`/marks/batches/${saved.id}/submit`)).data;
    },
    onSuccess: (submitted, vars) => {
      toast("Marks submitted and locked", "success");
      setSubmitConfirmOpen(false);
      adopt(vars, submitted);
    },
    onError: (e) => {
      onSaveError(e);
      setSubmitConfirmOpen(false);
    },
  });

  const requestEdit = useMutation({
    mutationFn: () => api.post(`/marks/batches/${batch!.id}/request-edit`, { reason: editReason.trim() }),
    onSuccess: () => {
      toast("Edit request sent to super-admin", "success");
      setRequestEditOpen(false);
      setEditReason("");
      refetchBatch();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  // Inputs are read-only while a save runs: its response replaces them.
  const saving = saveDraft.isPending || submitFinal.isPending;
  const batchRev = revisionKey(batch);
  // Load the saved marks into the inputs when this test's batch loads or changes, unless
  // the teacher has unsaved edits: those stay, and saving waits for a reload, since it
  // would put the outdated set back. (While this screen saves, its response settles them.)
  useEffect(() => {
    if (!batchLoaded || saving) return;
    const prev = shown.current;
    if (prev.test === testKey && prev.rev === batchRev) return;
    if (prev.test === testKey && dirty) {
      setStaleError(t("portal.marksEntry.changedElsewhere", "The saved marks for this test changed elsewhere. Reload to see them."));
      return;
    }
    showBatch(batch);
  }, [testKey, batchRev, batchLoaded, saving]);

  // ── Validation summary ─────────────────────────────────────────
  const enteredCount = useMemo(
    () => Object.values(marks).filter((v) => (isGraded ? v !== "" : markNumber(v) != null)).length,
    [marks, isGraded],
  );
  const overMaxCount = useMemo(() => {
    if (!selectedComponent || isGraded) return 0;
    return Object.values(marks).filter((v) => (markNumber(v) ?? 0) > maxMarks).length;
  }, [marks, maxMarks, selectedComponent, isGraded]);

  const canSave = !!selectedSubject && !!selectedComponent && batchLoaded && shown.current.test === testKey
    && !staleError && overMaxCount === 0 && !isLockedForMe && !hasPendingRequest;
  const canSubmit = canSave && enteredCount > 0;

  // ── Render ─────────────────────────────────────────────────────
  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.marksEntry")}</h1>
        {isAdmin && (
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <FileSpreadsheet className="h-4 w-4" /> Bulk import
          </Button>
        )}
      </div>

      <BulkImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bulk import marks"
        description={t(
          "portal.marksEntry.importHint",
          "One row per student per exam. Required: class_name, subject, exam_type (an exam component from Class Subjects, e.g. P.T. First), session (e.g. 2026-27), student_id, and marks (or grade, A1–D, for graded exams such as Term 1 Grade). Max marks come from Class Subjects. Rows are saved as draft batches, exactly like this form; submitted (locked) batches are rejected.",
        )}
        templateCsv={MARKS_TEMPLATE}
        templateFilename="marks-template.csv"
        uploadPath="/marks/bulk-import"
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ["marks-batch"] });
          qc.invalidateQueries({ queryKey: ["results"] });
        }}
      />

      <Card>
        <CardHeader><CardTitle>Exam details</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Class</Label>
            <Select value={cls} onValueChange={pick(cls, setCls)} disabled={saving || !allowed.length}>
              <SelectTrigger><SelectValue placeholder="Select class" /></SelectTrigger>
              <SelectContent>{allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
            {!allowed.length && (
              <p className="text-xs text-muted-foreground">
                {t("portal.common.noClassesAssigned", "No classes are assigned to your account yet. Ask an admin.")}
              </p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label>Subject</Label>
            <Select value={subjectId} onValueChange={pick(subjectId, setSubjectId)} disabled={!cls || saving}>
              <SelectTrigger>
                <SelectValue placeholder={!cls ? "Select class first" : "Select subject"} />
              </SelectTrigger>
              <SelectContent>
                {eligibleSubjects.length === 0 && cls ? (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">No subjects yet</div>
                ) : (
                  eligibleSubjects.map((s) => (
                    <SelectItem key={s.id} value={String(s.id)}>
                      {s.subject_name}
                      {s.category === "co_curricular" && ` — ${t("portal.marksEntry.coCurricularCounted", "co-curricular (counted in total)")}`}
                      {s.category === "grading" && ` — ${t("portal.marksEntry.graded", "graded")}`}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Test / Component</Label>
            <Select
              value={componentId}
              onValueChange={pick(componentId, setComponentId)}
              disabled={!subjectId || subjectDetailQ.isLoading || saving}
            >
              <SelectTrigger>
                <SelectValue placeholder={!subjectId ? "Select subject first" : "Select component"} />
              </SelectTrigger>
              <SelectContent>
                {components.length === 0 && subjectId ? (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">No components configured</div>
                ) : (
                  components.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.component_name} —{" "}
                      {c.max_marks === 0
                        ? t("portal.marksEntry.gradeOption", "grade")
                        : t("portal.marksEntry.maxOption", "max {{max}}", { max: c.max_marks })}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Max marks <span className="text-muted-foreground">— auto from master</span></Label>
            <Input
              value={!selectedComponent ? "" : isGraded ? t("portal.marksEntry.letterGrade", "Letter grade") : String(maxMarks)}
              readOnly
              disabled
              placeholder="—"
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="marks-session">Session</Label>
            <SessionSelect id="marks-session" value={session} onChange={pick(session, setSession)} disabled={saving} />
          </div>
        </CardContent>
      </Card>

      {/* Empty-state banners */}
      {cls && subjectsQ.isFetched && eligibleSubjects.length === 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-700 mt-0.5 shrink-0" />
          <div>
            No subjects are configured for {cls} yet.{" "}
            <Link to="/class-subjects" className="underline font-medium">
              Ask super-admin to set up Class Subjects
            </Link>.
          </div>
        </div>
      )}
      {subjectId && subjectDetailQ.isFetched && components.length === 0 && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm flex items-start gap-2">
          <BookOpen className="h-4 w-4 text-amber-700 mt-0.5 shrink-0" />
          <div>
            {selectedSubject?.subject_name} has no exam components yet.{" "}
            <Link to={`/class-subjects/${subjectId}`} className="underline font-medium">
              Configure components
            </Link>.
          </div>
        </div>
      )}

      {/* Status banners */}
      {batch && isLocked && hasPendingRequest && (
        <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm flex items-start gap-2">
          <Lock className="h-4 w-4 text-amber-700 mt-0.5 shrink-0" />
          <div>
            <b>Edit request pending super-admin review.</b> Once approved, the batch returns to draft and you can edit.
          </div>
        </div>
      )}
      {batch && isLocked && !hasPendingRequest && batch.last_rejection && (
        <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm flex items-start gap-2">
          <Lock className="h-4 w-4 text-red-700 mt-0.5 shrink-0" />
          <div>
            <b>Previous edit request rejected:</b> {batch.last_rejection}
          </div>
        </div>
      )}

      <Card>
        <CardHeader>
          <div className="flex items-center justify-between flex-wrap gap-2">
            <CardTitle>
              {selectedSubject && selectedComponent
                ? `${cls} — ${selectedSubject.subject_name} · ${selectedComponent.component_name}`
                : "Enter marks"}
            </CardTitle>
            {selectedComponent && (
              <div className="text-xs text-muted-foreground flex items-center gap-2">
                {batch?.status === "draft" && <Badge variant="warning">Draft</Badge>}
                {batch?.status === "submitted" && (
                  <Badge variant="success" className="gap-1">
                    <Lock className="h-3 w-3" /> Submitted
                  </Badge>
                )}
                {batchLoaded && !batch && <Badge variant="outline">New</Badge>}
                <Badge variant="outline">{isGraded ? t("portal.marksEntry.letterGrade", "Letter grade") : `Max ${maxMarks}`}</Badge>
                {enteredCount > 0 && <span>{enteredCount} entered</span>}
                {overMaxCount > 0 && <Badge variant="destructive">{overMaxCount} over max</Badge>}
              </div>
            )}
          </div>
          {batch?.submitted_at && (
            <div className="text-xs text-muted-foreground">
              Submitted by <b>{batch.submitted_by ?? "—"}</b> on {fmtTs(batch.submitted_at)}
            </div>
          )}
        </CardHeader>
        <CardContent>
          {!cls ? (
            <p className="text-muted-foreground text-sm">Select a class to load students.</p>
          ) : !sortedStudents.length ? (
            <p className="text-muted-foreground text-sm">No students in this class.</p>
          ) : !selectedComponent ? (
            <p className="text-muted-foreground text-sm">Pick a subject and a test component above.</p>
          ) : (
            <>
              {batchEnabled && batchQ.isPending && (
                <p className="text-sm text-muted-foreground mb-3">
                  {t("portal.marksEntry.loadingSaved", "Loading saved marks…")}
                </p>
              )}
              {batchQ.isError && (
                <div className="rounded-md border border-red-300 bg-red-50 p-3 text-sm flex items-start gap-2 mb-3">
                  <AlertTriangle className="h-4 w-4 text-red-700 mt-0.5 shrink-0" />
                  <div className="flex-1">
                    {t("portal.marksEntry.loadFailed", "Couldn't load the saved marks for this test, so editing is paused to protect them.")}{" "}
                    <span className="text-muted-foreground">{apiError(batchQ.error)}</span>
                  </div>
                  <Button size="sm" variant="outline" onClick={() => batchQ.refetch()}>
                    {t("portal.marksEntry.retry", "Retry")}
                  </Button>
                </div>
              )}
              {staleError && (
                <div className="rounded-md border border-amber-300 bg-amber-50 p-3 text-sm flex items-start gap-2 mb-3">
                  <AlertTriangle className="h-4 w-4 text-amber-700 mt-0.5 shrink-0" />
                  <div className="flex-1">{staleError}</div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      // Drops the unsaved edits (after asking) for the saved marks.
                      if (!confirmLeave()) return;
                      showBatch(batch);
                      refetchBatch();
                    }}
                  >
                    {t("portal.marksEntry.reloadSaved", "Reload saved marks")}
                  </Button>
                </div>
              )}
              <div className="space-y-2 mb-4">
                {sortedStudents.map((s) => {
                  const v = marks[s.id] ?? "";
                  // Names the row's input for screen readers ("Manveer Singh · P.T. First").
                  const entryLabel = `${s.name} · ${selectedComponent?.component_name ?? ""}`;
                  return (
                    <div key={s.id} className="flex items-center gap-3">
                      <span className="font-mono text-xs text-muted-foreground w-10 shrink-0 text-right">
                        {s.roll_no ?? "—"}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{s.name}</div>
                        {s.father && (
                          <div className="text-xs text-muted-foreground truncate">
                            S/o {s.father}
                          </div>
                        )}
                      </div>
                      {isGraded ? (
                        <Select
                          value={v || "none"}
                          onValueChange={(next) => setMarks({ ...marks, [s.id]: next === "none" ? "" : next })}
                          disabled={isLockedForMe || hasPendingRequest || !batchLoaded || saving}
                        >
                          <SelectTrigger className="w-28" aria-label={entryLabel}><SelectValue /></SelectTrigger>
                          <SelectContent>
                            <SelectItem value="none">—</SelectItem>
                            {gradeLetters.map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                          </SelectContent>
                        </Select>
                      ) : (
                        <NumberField
                          className="w-28 text-right"
                          aria-label={entryLabel}
                          placeholder="—"
                          value={v}
                          max={maxMarks}
                          min={0}
                          integer
                          disabled={isLockedForMe || hasPendingRequest || !batchLoaded || saving}
                          invalid={v !== "" && (Number(v) > maxMarks || Number(v) < 0)}
                          onChange={(next) => setMarks({ ...marks, [s.id]: next })}
                        />
                      )}
                      <span className="text-xs text-muted-foreground w-12 shrink-0">{isGraded ? "" : `/ ${maxMarks}`}</span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {!isLockedForMe && isLocked && (
                  // Super-admin edits a submitted batch in place; it stays locked.
                  <Button onClick={() => saveDraft.mutate({ test: testKey, key: batchKey })} disabled={!canSave || saving}>
                    <Save className="h-4 w-4" />{" "}
                    {saveDraft.isPending ? t("portal.common.saving", "Saving…") : t("portal.actions.saveChanges", "Save changes")}
                  </Button>
                )}
                {!isLockedForMe && !isLocked && (
                  <>
                    <Button variant="outline" onClick={() => saveDraft.mutate({ test: testKey, key: batchKey })} disabled={!canSave || saving}>
                      <Save className="h-4 w-4" /> {saveDraft.isPending ? "Saving…" : "Save draft"}
                    </Button>
                    <Button onClick={() => setSubmitConfirmOpen(true)} disabled={!canSubmit || saving}>
                      <Send className="h-4 w-4" /> {submitFinal.isPending ? "Submitting…" : "Submit final"}
                    </Button>
                  </>
                )}
                {isLockedForMe && !hasPendingRequest && (
                  <Button variant="outline" onClick={() => setRequestEditOpen(true)}>
                    <FilePen className="h-4 w-4" /> Request edit
                  </Button>
                )}
                {isLockedForMe && hasPendingRequest && (
                  <Button variant="outline" disabled>
                    <FilePen className="h-4 w-4" /> Edit request pending…
                  </Button>
                )}
              </div>
              {overMaxCount > 0 && (
                <p className="mt-2 text-xs text-destructive">
                  Fix {overMaxCount} entr{overMaxCount === 1 ? "y" : "ies"} above {maxMarks} before saving.
                </p>
              )}
            </>
          )}
        </CardContent>
      </Card>

      {/* Submit-final confirm */}
      <Dialog open={submitConfirmOpen} onOpenChange={setSubmitConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Submit and lock marks?</DialogTitle>
            <DialogDescription>
              After submitting, you won't be able to edit these marks without super-admin approval.
              Make sure all <b>{enteredCount}</b> entries for {selectedSubject?.subject_name} · {selectedComponent?.component_name} are correct.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSubmitConfirmOpen(false)}>Keep editing</Button>
            <Button onClick={() => submitFinal.mutate({ test: testKey, key: batchKey })} disabled={!canSubmit || saving}>
              <Send className="h-4 w-4" /> {submitFinal.isPending ? "Submitting…" : "Submit and lock"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Request-edit dialog */}
      <Dialog open={requestEditOpen} onOpenChange={(o) => { if (!o) { setRequestEditOpen(false); setEditReason(""); } }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Request permission to edit</DialogTitle>
            <DialogDescription>
              This batch is locked. Tell the super-admin why you need to edit — they'll approve or reject with their own note.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-1.5">
            <Label>Reason</Label>
            <Textarea
              value={editReason}
              onChange={(e) => setEditReason(e.target.value)}
              rows={4}
              placeholder="e.g. Arjun Singh's Maths PT-1 score was misread (29 → 39). Parent verified original answer sheet."
              maxLength={2000}
            />
            <div className="text-xs text-muted-foreground">{editReason.trim().length}/2000</div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setRequestEditOpen(false); setEditReason(""); }}>Cancel</Button>
            <Button
              onClick={() => requestEdit.mutate()}
              disabled={!editReason.trim() || requestEdit.isPending}
            >
              <FilePen className="h-4 w-4" /> {requestEdit.isPending ? "Sending…" : "Send request"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
