import { useMemo, useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
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
import type { Student, ClassSubject, ClassSubjectDetail, MarksBatchDetail } from "@/types/api";
import { useTranslation } from "react-i18next";

const defaultSession = () => {
  const y = new Date().getFullYear();
  return `${y}-${String((y + 1) % 100).padStart(2, "0")}`;
};

const fmtTs = (v: string | null): string => {
  if (!v) return "—";
  try { return new Date(v).toLocaleString(); } catch { return v; }
};

export default function MarksEntry() {
  const { t } = useTranslation();
  const { user, isAdmin, isSuperAdmin } = useAuth();
  // Super-admin and admin see every class; staff are limited to their allowed list.
  const allowed = isAdmin || !user?.allowed_classes?.length ? CLASSES : user.allowed_classes;

  const [cls, setCls] = useState("");
  const [subjectId, setSubjectId] = useState<string>("");
  const [componentId, setComponentId] = useState<string>("");
  const [session, setSession] = useState(defaultSession);
  const [marks, setMarks] = useState<Record<number, string>>({});
  const [importOpen, setImportOpen] = useState(false);
  const [submitConfirmOpen, setSubmitConfirmOpen] = useState(false);
  const [requestEditOpen, setRequestEditOpen] = useState(false);
  const [editReason, setEditReason] = useState("");
  const qc = useQueryClient();

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

  const eligibleSubjects = useMemo(
    () => (subjectsQ.data ?? []).filter((s) => s.category !== "grading"),
    [subjectsQ.data],
  );

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

  // ── Batch query (the load-existing-marks side) ─────────────────
  const batchEnabled = !!cls && !!selectedSubject && !!selectedComponent && !!session;
  const batchQ = useQuery<MarksBatchDetail | null>({
    queryKey: ["marks-batch", cls, selectedSubject?.subject_name, selectedComponent?.component_name, session],
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
  useSSE("marks_batches", [["marks-batch"]]);

  const batch = batchQ.data ?? null;
  const isLocked = batch?.status === "submitted";
  const isLockedForMe = isLocked && !isSuperAdmin;
  const hasPendingRequest = !!batch?.pending_edit_request_id;

  // Reset child selectors when parents change.
  useEffect(() => { setSubjectId(""); setComponentId(""); setMarks({}); }, [cls]);
  useEffect(() => { setComponentId(""); setMarks({}); }, [subjectId]);
  // When the loaded batch changes, hydrate the inputs from its rows.
  useEffect(() => {
    if (batch) {
      const next: Record<number, string> = {};
      for (const row of batch.items) next[row.student_id] = String(row.marks);
      setMarks(next);
    } else if (batchQ.isFetched) {
      setMarks({});
    }
  }, [batch?.id, batch?.updated_at, batchQ.isFetched]);

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
    items: Object.entries(marks)
      .filter(([, v]) => v !== "")
      .map(([id, v]) => ({ student_id: Number(id), marks: Number(v) })),
  });

  const refetchBatch = () => qc.invalidateQueries({ queryKey: ["marks-batch", cls, selectedSubject?.subject_name, selectedComponent?.component_name, session] });

  const saveDraft = useMutation({
    mutationFn: () => api.post("/marks/batches", buildPayload()),
    onSuccess: () => { toast("Draft saved", "success"); refetchBatch(); },
    onError: (e) => toast(apiError(e), "error"),
  });

  const submitFinal = useMutation({
    mutationFn: async () => {
      // Save then submit, so the latest unsaved edits land before lock.
      const saved = await api.post("/marks/batches", buildPayload());
      const batchId = (saved.data as MarksBatchDetail).id;
      return api.post(`/marks/batches/${batchId}/submit`);
    },
    onSuccess: () => {
      toast("Marks submitted and locked", "success");
      setSubmitConfirmOpen(false);
      refetchBatch();
    },
    onError: (e) => {
      toast(apiError(e), "error");
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

  // ── Validation summary ─────────────────────────────────────────
  const enteredCount = useMemo(
    () => Object.values(marks).filter((v) => v !== "").length,
    [marks],
  );
  const overMaxCount = useMemo(() => {
    if (!selectedComponent) return 0;
    return Object.values(marks).filter((v) => v !== "" && Number(v) > maxMarks).length;
  }, [marks, maxMarks, selectedComponent]);

  const canSave = !!selectedSubject && !!selectedComponent && overMaxCount === 0 && !isLockedForMe && !hasPendingRequest;
  const canSubmit = canSave && enteredCount > 0;

  // ── Render ─────────────────────────────────────────────────────
  return (
    <div className="space-y-4 max-w-4xl">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.marksEntry")}</h1>
        <Button variant="outline" onClick={() => setImportOpen(true)}>
          <FileSpreadsheet className="h-4 w-4" /> Bulk import
        </Button>
      </div>

      <BulkImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bulk import marks"
        description="One row per (student × subject). Required: class_name, exam_type, subject, student_id, marks. Defaults: max_marks=100, session=blank. Bulk imports bypass the batch / lock workflow — use the form below for normal entry."
        templateCsv={MARKS_TEMPLATE}
        templateFilename="marks-template.csv"
        uploadPath="/marks/bulk-import"
        onSuccess={() => qc.invalidateQueries({ queryKey: ["marks"] })}
      />

      <Card>
        <CardHeader><CardTitle>Exam details</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="space-y-1.5">
            <Label>Class</Label>
            <Select value={cls} onValueChange={setCls}>
              <SelectTrigger><SelectValue placeholder="Select class" /></SelectTrigger>
              <SelectContent>{allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Subject</Label>
            <Select value={subjectId} onValueChange={setSubjectId} disabled={!cls}>
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
                      {s.category === "co_curricular" && " — co-curricular"}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Test / Component</Label>
            <Select value={componentId} onValueChange={setComponentId} disabled={!subjectId || subjectDetailQ.isLoading}>
              <SelectTrigger>
                <SelectValue placeholder={!subjectId ? "Select subject first" : "Select component"} />
              </SelectTrigger>
              <SelectContent>
                {components.length === 0 && subjectId ? (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">No components configured</div>
                ) : (
                  components.map((c) => (
                    <SelectItem key={c.id} value={String(c.id)}>
                      {c.component_name} — max {c.max_marks}
                    </SelectItem>
                  ))
                )}
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Max marks <span className="text-muted-foreground">— auto from master</span></Label>
            <Input value={selectedComponent ? String(maxMarks) : ""} readOnly disabled placeholder="—" />
          </div>
          <div className="space-y-1.5">
            <Label>Session</Label>
            <Input value={session} onChange={(e) => setSession(e.target.value)} placeholder="2025-26" />
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
                {!batch && <Badge variant="outline">New</Badge>}
                <Badge variant="outline">Max {maxMarks}</Badge>
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
              <div className="space-y-2 mb-4">
                {sortedStudents.map((s) => {
                  const v = marks[s.id] ?? "";
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
                      <NumberField
                        className="w-28 text-right"
                        placeholder="—"
                        value={v}
                        max={maxMarks}
                        min={0}
                        disabled={isLockedForMe || hasPendingRequest}
                        invalid={v !== "" && (Number(v) > maxMarks || Number(v) < 0)}
                        onChange={(next) => setMarks({ ...marks, [s.id]: next })}
                      />
                      <span className="text-xs text-muted-foreground w-12 shrink-0">/ {maxMarks}</span>
                    </div>
                  );
                })}
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                {!isLockedForMe && (
                  <>
                    <Button variant="outline" onClick={() => saveDraft.mutate()} disabled={!canSave || saveDraft.isPending}>
                      <Save className="h-4 w-4" /> {saveDraft.isPending ? "Saving…" : "Save draft"}
                    </Button>
                    <Button onClick={() => setSubmitConfirmOpen(true)} disabled={!canSubmit || submitFinal.isPending}>
                      <Send className="h-4 w-4" /> {submitFinal.isPending ? "Submitting…" : isSuperAdmin && isLocked ? "Re-submit" : "Submit final"}
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
            <Button onClick={() => submitFinal.mutate()} disabled={submitFinal.isPending}>
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
