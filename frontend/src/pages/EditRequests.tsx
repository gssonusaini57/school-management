import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, XCircle, FileEdit, Eye, BookOpen } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { fieldLabel, diffValue } from "@/lib/student-labels";
import type { EditRequestItem, MarksEditRequestItem } from "@/types/api";

interface QueueResponse { items: EditRequestItem[] }
interface MarksQueueResponse { items: MarksEditRequestItem[] }

function fmtTs(v: string | null): string {
  if (!v) return "—";
  try { return new Date(v).toLocaleString(); } catch { return v; }
}

export default function EditRequests() {
  const qc = useQueryClient();

  // ── Student edit-requests queue (existing) ─────────────────────
  const [reviewing, setReviewing] = useState<EditRequestItem | null>(null);
  const [rejectMode, setRejectMode] = useState(false);
  const [rejectReason, setRejectReason] = useState("");

  const { data, isFetching } = useQuery<QueueResponse>({
    queryKey: ["edit-requests"],
    queryFn: () => api.get("/admin/edit-requests").then((r) => r.data),
  });
  useSSE("edit_requests", [["edit-requests"], ["students"], ["student"]]);

  const pending = useMemo(
    () => (data?.items ?? []).filter((r) => r.status === "pending"),
    [data],
  );
  const reviewed = useMemo(
    () => (data?.items ?? []).filter((r) => r.status !== "pending"),
    [data],
  );

  const approve = useMutation({
    mutationFn: (id: number) => api.post(`/admin/edit-requests/${id}/approve`),
    onSuccess: () => {
      toast("Edit approved", "success");
      qc.invalidateQueries({ queryKey: ["edit-requests"] });
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["student"] });
      closeReview();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const reject = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      api.post(`/admin/edit-requests/${id}/reject`, { reason: reason || null }),
    onSuccess: () => {
      toast("Edit rejected", "warning");
      qc.invalidateQueries({ queryKey: ["edit-requests"] });
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["student"] });
      closeReview();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const openReview = (r: EditRequestItem) => {
    setReviewing(r);
    setRejectMode(false);
    setRejectReason("");
  };
  const closeReview = () => {
    setReviewing(null);
    setRejectMode(false);
    setRejectReason("");
  };

  // ── Marks edit-requests queue (new) ────────────────────────────
  const [marksReviewing, setMarksReviewing] = useState<MarksEditRequestItem | null>(null);
  const [marksRejectMode, setMarksRejectMode] = useState(false);
  const [marksRejectReason, setMarksRejectReason] = useState("");

  const marksQ = useQuery<MarksQueueResponse>({
    queryKey: ["marks-edit-requests"],
    queryFn: () => api.get("/admin/marks-edit-requests").then((r) => r.data),
  });
  useSSE("marks_edit_requests", [["marks-edit-requests"], ["marks-batch"]]);

  const marksPending = useMemo(
    () => (marksQ.data?.items ?? []).filter((r) => r.status === "pending"),
    [marksQ.data],
  );
  const marksReviewed = useMemo(
    () => (marksQ.data?.items ?? []).filter((r) => r.status !== "pending"),
    [marksQ.data],
  );

  const approveMarks = useMutation({
    mutationFn: (id: number) => api.post(`/admin/marks-edit-requests/${id}/approve`),
    onSuccess: () => {
      toast("Edit approved — batch unlocked for re-entry", "success");
      qc.invalidateQueries({ queryKey: ["marks-edit-requests"] });
      qc.invalidateQueries({ queryKey: ["marks-batch"] });
      closeMarksReview();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const rejectMarks = useMutation({
    mutationFn: ({ id, reason }: { id: number; reason: string }) =>
      api.post(`/admin/marks-edit-requests/${id}/reject`, { reason: reason || null }),
    onSuccess: () => {
      toast("Edit rejected", "warning");
      qc.invalidateQueries({ queryKey: ["marks-edit-requests"] });
      qc.invalidateQueries({ queryKey: ["marks-batch"] });
      closeMarksReview();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const openMarksReview = (r: MarksEditRequestItem) => {
    setMarksReviewing(r);
    setMarksRejectMode(false);
    setMarksRejectReason("");
  };
  const closeMarksReview = () => {
    setMarksReviewing(null);
    setMarksRejectMode(false);
    setMarksRejectReason("");
  };

  const totalPending = pending.length + marksPending.length;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">Edit Requests</h1>
        <div className="text-xs text-muted-foreground">
          {isFetching || marksQ.isFetching ? "loading…" : `${totalPending} pending across both queues`}
        </div>
      </div>

      <Tabs defaultValue={marksPending.length > 0 && pending.length === 0 ? "marks" : "student"}>
        <TabsList>
          <TabsTrigger value="student">
            Student edits
            {pending.length > 0 && <Badge variant="warning" className="ml-2 h-5 px-1.5">{pending.length}</Badge>}
          </TabsTrigger>
          <TabsTrigger value="marks">
            Marks edits
            {marksPending.length > 0 && <Badge variant="warning" className="ml-2 h-5 px-1.5">{marksPending.length}</Badge>}
          </TabsTrigger>
        </TabsList>

        {/* ── Student edits tab (unchanged) ─────────────────────── */}
        <TabsContent value="student" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-amber-700">
                <FileEdit className="h-4 w-4" /> Pending approval ({pending.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student</TableHead>
                    <TableHead>Class</TableHead>
                    <TableHead>Requested by</TableHead>
                    <TableHead>Requested at</TableHead>
                    <TableHead>Fields</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {pending.map((r) => (
                    <TableRow key={r.id} className="bg-amber-50/40">
                      <TableCell className="font-medium">{r.student_name}</TableCell>
                      <TableCell>{r.class_name ? <Badge variant="info">{r.class_name}</Badge> : "—"}</TableCell>
                      <TableCell className="text-sm">
                        {r.requested_by}
                        <span className="ml-1 text-muted-foreground text-xs">({r.requested_by_role})</span>
                      </TableCell>
                      <TableCell className="text-xs">{fmtTs(r.requested_at)}</TableCell>
                      <TableCell className="text-xs">{Object.keys(r.changes).length}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="default" onClick={() => openReview(r)}>
                          <Eye className="h-4 w-4" /> Review
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!pending.length && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-6">
                        No pending edit requests
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-muted-foreground">Recently reviewed ({reviewed.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Student</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Requested by</TableHead>
                    <TableHead>Reviewed by</TableHead>
                    <TableHead>Reviewed at</TableHead>
                    <TableHead>Reject reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {reviewed.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell className="font-medium">{r.student_name}</TableCell>
                      <TableCell>
                        {r.status === "approved" ? (
                          <Badge variant="success">Approved</Badge>
                        ) : (
                          <Badge variant="destructive">Rejected</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{r.requested_by}</TableCell>
                      <TableCell className="text-sm">{r.reviewed_by ?? "—"}</TableCell>
                      <TableCell className="text-xs">{fmtTs(r.reviewed_at)}</TableCell>
                      <TableCell className="text-sm max-w-xs truncate" title={r.reject_reason ?? undefined}>
                        {r.reject_reason ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                  {!reviewed.length && (
                    <TableRow>
                      <TableCell colSpan={6} className="text-center text-muted-foreground py-6">
                        No reviewed requests yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>

        {/* ── Marks edits tab (new) ────────────────────────────── */}
        <TabsContent value="marks" className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-amber-700">
                <BookOpen className="h-4 w-4" /> Pending approval ({marksPending.length})
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Class</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Component</TableHead>
                    <TableHead>Session</TableHead>
                    <TableHead>Students</TableHead>
                    <TableHead>Requested by</TableHead>
                    <TableHead>Requested at</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {marksPending.map((r) => (
                    <TableRow key={r.id} className="bg-amber-50/40">
                      <TableCell><Badge variant="info">{r.class_name}</Badge></TableCell>
                      <TableCell className="font-medium">{r.subject}</TableCell>
                      <TableCell className="text-sm">{r.exam_type}</TableCell>
                      <TableCell className="text-xs font-mono">{r.session}</TableCell>
                      <TableCell className="text-xs">{r.student_count}</TableCell>
                      <TableCell className="text-sm">
                        {r.requested_by}
                        <span className="ml-1 text-muted-foreground text-xs">({r.requested_by_role})</span>
                      </TableCell>
                      <TableCell className="text-xs">{fmtTs(r.requested_at)}</TableCell>
                      <TableCell className="text-right">
                        <Button size="sm" variant="default" onClick={() => openMarksReview(r)}>
                          <Eye className="h-4 w-4" /> Review
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!marksPending.length && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground py-6">
                        No pending marks-edit requests
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-muted-foreground">Recently reviewed ({marksReviewed.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Class</TableHead>
                    <TableHead>Subject</TableHead>
                    <TableHead>Component</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead>Requested by</TableHead>
                    <TableHead>Reviewed by</TableHead>
                    <TableHead>Reviewed at</TableHead>
                    <TableHead>Reject reason</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {marksReviewed.map((r) => (
                    <TableRow key={r.id}>
                      <TableCell><Badge variant="info">{r.class_name}</Badge></TableCell>
                      <TableCell className="font-medium">{r.subject}</TableCell>
                      <TableCell className="text-sm">{r.exam_type}</TableCell>
                      <TableCell>
                        {r.status === "approved" ? (
                          <Badge variant="success">Approved</Badge>
                        ) : (
                          <Badge variant="destructive">Rejected</Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm">{r.requested_by}</TableCell>
                      <TableCell className="text-sm">{r.reviewed_by ?? "—"}</TableCell>
                      <TableCell className="text-xs">{fmtTs(r.reviewed_at)}</TableCell>
                      <TableCell className="text-sm max-w-xs truncate" title={r.reject_reason ?? undefined}>
                        {r.reject_reason ?? "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                  {!marksReviewed.length && (
                    <TableRow>
                      <TableCell colSpan={8} className="text-center text-muted-foreground py-6">
                        No reviewed requests yet
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* ── Student review modal (unchanged) ──────────────────── */}
      <Dialog open={!!reviewing} onOpenChange={(o) => { if (!o) closeReview(); }}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              Review edit · {reviewing?.student_name}
              {reviewing?.class_name && (
                <Badge variant="info" className="ml-2">{reviewing.class_name}</Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              Requested by <b>{reviewing?.requested_by}</b> ({reviewing?.requested_by_role}) at{" "}
              {fmtTs(reviewing?.requested_at ?? null)}. Approve to apply every change; reject to discard.
            </DialogDescription>
          </DialogHeader>

          {reviewing && (
            <div className="border rounded-md overflow-hidden">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead className="w-1/3">Field</TableHead>
                    <TableHead className="w-1/3">Old value</TableHead>
                    <TableHead className="w-1/3">New value</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {Object.entries(reviewing.changes).map(([key, pair]) => (
                    <TableRow key={key}>
                      <TableCell className="font-medium">{fieldLabel(key)}</TableCell>
                      <TableCell className="text-sm bg-red-50/60">
                        <span className="line-through text-red-700">{diffValue(pair.old)}</span>
                      </TableCell>
                      <TableCell className="text-sm bg-emerald-50/60 font-medium text-emerald-800">
                        {diffValue(pair.new)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}

          {rejectMode && (
            <div className="space-y-1.5">
              <div className="text-sm font-medium">Reject reason (optional)</div>
              <Textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                rows={3}
                placeholder="Visible to admin/staff in the reviewed list"
                maxLength={500}
              />
            </div>
          )}

          <DialogFooter className="gap-2">
            {!rejectMode ? (
              <>
                <Button variant="outline" onClick={closeReview}>Cancel</Button>
                <Button
                  variant="outline"
                  className="text-red-700 border-red-300 hover:bg-red-50"
                  onClick={() => setRejectMode(true)}
                >
                  <XCircle className="h-4 w-4" /> Reject…
                </Button>
                <Button
                  disabled={!reviewing || approve.isPending}
                  onClick={() => reviewing && approve.mutate(reviewing.id)}
                >
                  <CheckCircle2 className="h-4 w-4" /> Approve
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => { setRejectMode(false); setRejectReason(""); }}>
                  Back
                </Button>
                <Button
                  variant="destructive"
                  disabled={!reviewing || reject.isPending}
                  onClick={() => reviewing && reject.mutate({ id: reviewing.id, reason: rejectReason })}
                >
                  <XCircle className="h-4 w-4" /> Confirm reject
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Marks review modal (new) ─────────────────────────── */}
      <Dialog open={!!marksReviewing} onOpenChange={(o) => { if (!o) closeMarksReview(); }}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>
              Marks edit · {marksReviewing?.subject}
              {marksReviewing?.class_name && (
                <Badge variant="info" className="ml-2">{marksReviewing.class_name}</Badge>
              )}
            </DialogTitle>
            <DialogDescription>
              Requested by <b>{marksReviewing?.requested_by}</b> ({marksReviewing?.requested_by_role}) at{" "}
              {fmtTs(marksReviewing?.requested_at ?? null)}.
              Approving unlocks the batch so the teacher can edit and re-submit.
            </DialogDescription>
          </DialogHeader>

          {marksReviewing && (
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs text-muted-foreground">Component</div>
                  <div className="font-medium">{marksReviewing.exam_type}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Session</div>
                  <div className="font-mono">{marksReviewing.session}</div>
                </div>
                <div>
                  <div className="text-xs text-muted-foreground">Students entered</div>
                  <div className="font-medium">{marksReviewing.student_count}</div>
                </div>
              </div>

              <div>
                <div className="text-xs text-muted-foreground mb-1">Teacher's reason</div>
                <div className="rounded-md border bg-cream/40 p-3 text-sm whitespace-pre-wrap">
                  {marksReviewing.reason}
                </div>
              </div>
            </div>
          )}

          {marksRejectMode && (
            <div className="space-y-1.5">
              <div className="text-sm font-medium">Reject reason (optional)</div>
              <Textarea
                value={marksRejectReason}
                onChange={(e) => setMarksRejectReason(e.target.value)}
                rows={3}
                placeholder="Visible to the teacher when the batch stays locked"
                maxLength={500}
              />
            </div>
          )}

          <DialogFooter className="gap-2">
            {!marksRejectMode ? (
              <>
                <Button variant="outline" onClick={closeMarksReview}>Cancel</Button>
                <Button
                  variant="outline"
                  className="text-red-700 border-red-300 hover:bg-red-50"
                  onClick={() => setMarksRejectMode(true)}
                >
                  <XCircle className="h-4 w-4" /> Reject…
                </Button>
                <Button
                  disabled={!marksReviewing || approveMarks.isPending}
                  onClick={() => marksReviewing && approveMarks.mutate(marksReviewing.id)}
                >
                  <CheckCircle2 className="h-4 w-4" /> Approve
                </Button>
              </>
            ) : (
              <>
                <Button variant="outline" onClick={() => { setMarksRejectMode(false); setMarksRejectReason(""); }}>
                  Back
                </Button>
                <Button
                  variant="destructive"
                  disabled={!marksReviewing || rejectMarks.isPending}
                  onClick={() => marksReviewing && rejectMarks.mutate({ id: marksReviewing.id, reason: marksRejectReason })}
                >
                  <XCircle className="h-4 w-4" /> Confirm reject
                </Button>
              </>
            )}
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
