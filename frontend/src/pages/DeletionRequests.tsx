import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, RotateCcw, Trash2, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import type { DeletionRequestItem } from "@/types/api";
import { useTranslation } from "react-i18next";

interface QueueResponse { items: DeletionRequestItem[] }

function fmtTs(v: string | null): string {
  if (!v) return "—";
  try { return new Date(v).toLocaleString(); } catch { return v; }
}

export default function DeletionRequests() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const [purgeTarget, setPurgeTarget] = useState<DeletionRequestItem | null>(null);

  const { data, isFetching } = useQuery<QueueResponse>({
    queryKey: ["deletion-requests"],
    queryFn: () => api.get("/admin/deletion-requests").then((r) => r.data),
  });
  // SSE: any change on students/staff or the queue invalidates.
  useSSE("deletion_requests", [["deletion-requests"], ["students"], ["staff"]]);

  const pending = useMemo(
    () => (data?.items ?? []).filter((r) => r.status === "pending_delete"),
    [data]
  );
  const archived = useMemo(
    () => (data?.items ?? []).filter((r) => r.status === "deleted"),
    [data]
  );

  const approve = useMutation({
    mutationFn: ({ kind, id }: { kind: "student" | "staff"; id: number }) =>
      api.post(`/admin/deletion-requests/${kind}/${id}/approve`),
    onSuccess: () => {
      toast("Approved — record archived", "success");
      qc.invalidateQueries({ queryKey: ["deletion-requests"] });
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["staff"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const restore = useMutation({
    mutationFn: ({ kind, id }: { kind: "student" | "staff"; id: number }) =>
      api.post(`/admin/deletion-requests/${kind}/${id}/restore`),
    onSuccess: () => {
      toast("Restored", "success");
      qc.invalidateQueries({ queryKey: ["deletion-requests"] });
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["staff"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const purge = useMutation({
    mutationFn: ({ kind, id }: { kind: "student" | "staff"; id: number }) =>
      api.delete(`/admin/deletion-requests/${kind}/${id}`),
    onSuccess: () => {
      toast("Permanently deleted", "warning");
      qc.invalidateQueries({ queryKey: ["deletion-requests"] });
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["staff"] });
      setPurgeTarget(null);
    },
    onError: (e) => { toast(apiError(e), "error"); setPurgeTarget(null); },
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.deletionRequests", "Pending Deletions")}</h1>
        <div className="text-xs text-muted-foreground">
          {isFetching ? "loading…" : `${pending.length} pending · ${archived.length} archived`}
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-amber-700">
            <ShieldAlert className="h-4 w-4" /> Pending approval ({pending.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kind</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Context</TableHead>
                <TableHead>Requested by</TableHead>
                <TableHead>Requested at</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {pending.map((r) => (
                <TableRow key={`${r.kind}-${r.id}`} className="bg-amber-50/40">
                  <TableCell><Badge variant="warning">{r.kind}</Badge></TableCell>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {r.kind === "student" ? (r.class_name ?? "—") : (r.designation ?? "—")}
                  </TableCell>
                  <TableCell>{r.delete_requested_by ?? "—"}</TableCell>
                  <TableCell className="text-xs">{fmtTs(r.delete_requested_at)}</TableCell>
                  <TableCell className="text-sm max-w-xs truncate" title={r.delete_reason ?? undefined}>
                    {r.delete_reason ?? "—"}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <div className="flex gap-1 justify-end">
                      <Button
                        size="sm"
                        variant="default"
                        disabled={approve.isPending}
                        onClick={() => approve.mutate({ kind: r.kind, id: r.id })}
                      >
                        <CheckCircle2 className="h-4 w-4" /> Approve
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={restore.isPending}
                        onClick={() => restore.mutate({ kind: r.kind, id: r.id })}
                      >
                        <RotateCcw className="h-4 w-4" /> Restore
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!pending.length && (
                <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground py-6">No pending requests</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-red-700">
            <Trash2 className="h-4 w-4" /> Archived ({archived.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-xs text-muted-foreground mb-2">
            Already approved for deletion — hidden from normal lists. Restore brings them back. Purge permanently
            removes the row and all related data (documents, attendance, marks, fees, class assignments) and cannot be undone.
          </p>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kind</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Context</TableHead>
                <TableHead>Archived by</TableHead>
                <TableHead>Archived at</TableHead>
                <TableHead>Reason</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {archived.map((r) => (
                <TableRow key={`${r.kind}-${r.id}`}>
                  <TableCell><Badge variant="destructive">{r.kind}</Badge></TableCell>
                  <TableCell className="font-medium">{r.name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {r.kind === "student" ? (r.class_name ?? "—") : (r.designation ?? "—")}
                  </TableCell>
                  <TableCell>{r.deleted_by ?? "—"}</TableCell>
                  <TableCell className="text-xs">{fmtTs(r.deleted_at)}</TableCell>
                  <TableCell className="text-sm max-w-xs truncate" title={r.delete_reason ?? undefined}>
                    {r.delete_reason ?? "—"}
                  </TableCell>
                  <TableCell className="text-right whitespace-nowrap">
                    <div className="flex gap-1 justify-end">
                      <Button
                        size="sm"
                        variant="outline"
                        disabled={restore.isPending}
                        onClick={() => restore.mutate({ kind: r.kind, id: r.id })}
                      >
                        <RotateCcw className="h-4 w-4" /> Restore
                      </Button>
                      <Button
                        size="sm"
                        variant="destructive"
                        onClick={() => setPurgeTarget(r)}
                      >
                        <Trash2 className="h-4 w-4" /> Purge
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
              {!archived.length && (
                <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground py-6">No archived records</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={!!purgeTarget} onOpenChange={(o) => { if (!o) setPurgeTarget(null); }}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-red-700">Permanently delete {purgeTarget?.name}?</DialogTitle>
            <DialogDescription>
              This will hard-delete the {purgeTarget?.kind} record and cascade to all related data
              {purgeTarget?.kind === "student"
                ? " (documents, attendance, marks, fees)"
                : " (class assignments)"}.
              <span className="block mt-2 text-red-600 font-semibold">This action cannot be undone.</span>
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setPurgeTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={purge.isPending}
              onClick={() => purgeTarget && purge.mutate({ kind: purgeTarget.kind, id: purgeTarget.id })}
            >
              {purge.isPending ? "Deleting…" : "Permanently delete"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
