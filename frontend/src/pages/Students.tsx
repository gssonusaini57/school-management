import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient, keepPreviousData } from "@tanstack/react-query";
import { Eye, Pencil, Trash2, Search, Download, FileSpreadsheet, Clock, ChevronsLeft, ChevronLeft, ChevronRight, ChevronsRight } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Table, TableHead, TableHeader, TableBody, TableRow, TableCell } from "@/components/ui/table";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { CLASSES } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { STUDENTS_TEMPLATE } from "@/lib/templates";
import type { Student, StudentPage } from "@/types/api";
import { useTranslation } from "react-i18next";

const PAGE_SIZES = [5, 10, 25, 50, 100];
const DEFAULT_PAGE_SIZE = 10;

export default function Students() {
  const { t } = useTranslation();
  const { isAdmin, isSuperAdmin, user } = useAuth();
  // Admin has empty allowed_classes (full access) → show all CLASSES in filter.
  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;
  const qc = useQueryClient();

  // URL is the source of truth for class/search/page so refresh + back-button work.
  const [sp, setSp] = useSearchParams();
  const filter = sp.get("class") ?? "";
  const urlSearch = sp.get("q") ?? "";
  const page = Math.max(1, Number(sp.get("page") ?? "1") || 1);
  const pageSize = (() => {
    const n = Number(sp.get("size") ?? DEFAULT_PAGE_SIZE);
    return PAGE_SIZES.includes(n) ? n : DEFAULT_PAGE_SIZE;
  })();

  // Local input mirror; debounced into URL so we don't hammer the API on every keystroke.
  const [search, setSearch] = useState(urlSearch);
  useEffect(() => { setSearch(urlSearch); }, [urlSearch]);
  useEffect(() => {
    const handle = setTimeout(() => {
      if (search === urlSearch) return;
      setSp((s) => {
        const next = new URLSearchParams(s);
        if (search) next.set("q", search); else next.delete("q");
        next.set("page", "1");
        return next;
      }, { replace: true });
    }, 300);
    return () => clearTimeout(handle);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const setParam = (k: string, v: string | null) => {
    setSp((s) => {
      const next = new URLSearchParams(s);
      if (v) next.set(k, v); else next.delete(k);
      if (k !== "page") next.set("page", "1");
      return next;
    });
  };

  const [importOpen, setImportOpen] = useState(false);
  const [deleteTarget, setDeleteTarget] = useState<Student | null>(null);

  const queryKey = ["students", { filter, q: urlSearch, page, pageSize }] as const;
  const { data, isFetching, isPlaceholderData } = useQuery<StudentPage>({
    queryKey,
    queryFn: () =>
      api
        .get<StudentPage>("/students", {
          params: {
            ...(filter && { class: filter }),
            ...(urlSearch && { q: urlSearch }),
            page,
            page_size: pageSize,
          },
        })
        .then((r) => r.data),
    placeholderData: keepPreviousData,
  });

  // Re-fetch on any students-channel SSE event regardless of pagination state.
  useSSE("students", [["students"]]);

  const items = (data?.items ?? []).filter((s) => allowed.includes(s.class_name) || isAdmin);
  const total = data?.total ?? 0;
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const startRow = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const endRow = Math.min(total, page * pageSize);

  const exportCsv = () => {
    const rows = [["#", "Adm. ID", "Roll", "Name", "Father", "Class", "DOB", "Village", "Phone", "Aadhaar"]];
    items.forEach((s, i) =>
      rows.push([
        String(startRow + i),
        s.admission_id ?? "",
        s.roll_no ?? "",
        s.name,
        s.father,
        s.class_name,
        s.dob ?? "",
        s.village,
        s.phone,
        s.aadhar,
      ])
    );
    const a = document.createElement("a");
    a.href = "data:text/csv;charset=utf-8," + encodeURIComponent(rows.map((r) => r.join(",")).join("\n"));
    a.download = `KIS_Students_${filter || "All"}_p${page}_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.students")}</h1>
        <div className="flex gap-2">
          {isAdmin && (
            <Button variant="outline" onClick={() => setImportOpen(true)}>
              <FileSpreadsheet className="h-4 w-4" /> Bulk import
            </Button>
          )}
          <Button variant="outline" onClick={exportCsv}><Download className="h-4 w-4" /> Export CSV</Button>
        </div>
      </div>

      <BulkImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bulk import students"
        description="One student per row. Required: name, father, mother, phone (10 digits), class_name. Optional: admission_no (integer, unique school-wide), roll_no (unique within class). Aadhaar must be 12 digits if provided. Dates accepted as YYYY-MM-DD, DD-MM-YYYY, or DD/MM/YYYY (Excel often auto-converts; all three work). Names auto-Title-Cased."
        templateCsv={STUDENTS_TEMPLATE}
        templateFilename="students-template.csv"
        uploadPath="/students/bulk-import"
        onSuccess={() => qc.invalidateQueries({ queryKey: ["students"] })}
      />

      <DeleteStudentDialog
        student={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        isSuperAdmin={!!isSuperAdmin}
      />

      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
            <div className="space-y-1.5">
              <Label>Filter by class</Label>
              <Select
                value={filter || "__all"}
                onValueChange={(v) => setParam("class", v === "__all" ? null : v)}
              >
                <SelectTrigger><SelectValue placeholder="All classes" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all">All classes</SelectItem>
                  {allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5 sm:col-span-2">
              <Label>Search (name / father / phone / village / adm. ID)</Label>
              <div className="relative">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input value={search} onChange={(e) => setSearch(e.target.value)} className="pl-8" placeholder="Type to search…" />
              </div>
            </div>
          </div>
          <div className="text-xs text-muted-foreground mb-2">
            {total === 0
              ? "No results"
              : `Showing ${startRow}–${endRow} of ${total}${filter ? ` in ${filter}` : ""}`}
            {(isFetching || isPlaceholderData) && " · loading…"}
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>#</TableHead>
                <TableHead>Adm. ID</TableHead>
                <TableHead>Roll</TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Father</TableHead>
                <TableHead>Class</TableHead>
                <TableHead>DOB</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {items.map((s, i) => {
                const pending = s.status === "pending_delete";
                return (
                  <TableRow key={s.id} className={pending ? "bg-amber-50/60" : undefined}>
                    <TableCell>{startRow + i}</TableCell>
                    <TableCell className="font-mono text-xs">{s.admission_id ?? "—"}</TableCell>
                    <TableCell>{s.roll_no ?? "—"}</TableCell>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span>{s.name}</span>
                        {pending && (
                          <Badge variant="warning" className="gap-1">
                            <Clock className="h-3 w-3" /> Deletion requested
                          </Badge>
                        )}
                      </div>
                      {pending && s.delete_reason && (
                        <div className="text-xs text-muted-foreground mt-0.5">Reason: {s.delete_reason}</div>
                      )}
                    </TableCell>
                    <TableCell>{s.father}</TableCell>
                    <TableCell><Badge variant="info">{s.class_name}</Badge></TableCell>
                    <TableCell>{s.dob ?? "—"}</TableCell>
                    <TableCell>{s.phone || "—"}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex gap-1 justify-end">
                        <Button asChild size="icon" variant="outline"><Link to={`/students/${s.id}`}><Eye className="h-4 w-4" /></Link></Button>
                        <Button asChild size="icon" variant="outline"><Link to={`/students/${s.id}?edit=1`}><Pencil className="h-4 w-4" /></Link></Button>
                        {!pending && (
                          <Button
                            size="icon"
                            variant="outline"
                            className="text-red-600 hover:bg-red-50"
                            onClick={() => setDeleteTarget(s)}
                            aria-label={isSuperAdmin ? "Delete" : "Request delete"}
                          >
                            <Trash2 className="h-4 w-4" />
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                );
              })}
              {!items.length && (
                <TableRow><TableCell colSpan={9} className="text-center text-muted-foreground py-8">No students found</TableCell></TableRow>
              )}
            </TableBody>
          </Table>

          <div className="flex items-center justify-between gap-3 mt-3 flex-wrap text-sm">
            <div className="flex items-center gap-2">
              <span className="text-muted-foreground">Rows per page</span>
              <Select
                value={String(pageSize)}
                onValueChange={(v) => setParam("size", v)}
              >
                <SelectTrigger className="w-20"><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAGE_SIZES.map((n) => <SelectItem key={n} value={String(n)}>{n}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="text-muted-foreground">Page <b className="text-foreground">{page}</b> of <b className="text-foreground">{pageCount}</b></div>
            <div className="flex items-center gap-1">
              <Button size="icon" variant="outline" disabled={page <= 1} onClick={() => setParam("page", "1")} aria-label="First page"><ChevronsLeft className="h-4 w-4" /></Button>
              <Button size="icon" variant="outline" disabled={page <= 1} onClick={() => setParam("page", String(page - 1))} aria-label="Previous page"><ChevronLeft className="h-4 w-4" /></Button>
              <Button size="icon" variant="outline" disabled={page >= pageCount} onClick={() => setParam("page", String(page + 1))} aria-label="Next page"><ChevronRight className="h-4 w-4" /></Button>
              <Button size="icon" variant="outline" disabled={page >= pageCount} onClick={() => setParam("page", String(pageCount))} aria-label="Last page"><ChevronsRight className="h-4 w-4" /></Button>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function DeleteStudentDialog({
  student,
  onClose,
  isSuperAdmin,
}: {
  student: Student | null;
  onClose: () => void;
  isSuperAdmin: boolean;
}) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const open = !!student;

  const mut = useMutation({
    mutationFn: () => {
      if (!student) throw new Error("No student");
      return api.delete(`/students/${student.id}`, { data: { reason: reason || null } });
    },
    onSuccess: () => {
      toast(isSuperAdmin ? "Student archived" : "Deletion requested for super-admin approval", "warning");
      qc.invalidateQueries({ queryKey: ["students"] });
      qc.invalidateQueries({ queryKey: ["deletion-requests"] });
      setReason("");
      onClose();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) { setReason(""); onClose(); }
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isSuperAdmin ? "Archive student" : "Request student deletion"}</DialogTitle>
          <DialogDescription>
            {isSuperAdmin
              ? <>This will move <b>{student?.name}</b> to the archive (recoverable). Use the Pending Deletions page to purge or restore.</>
              : <>Submit <b>{student?.name}</b> for super-admin approval. The record stays visible with a "Deletion requested" badge until approved.</>}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>Reason (optional)</Label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. duplicate record, left school"
            rows={3}
            maxLength={500}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => { setReason(""); onClose(); }}>Cancel</Button>
          <Button
            variant="destructive"
            disabled={mut.isPending}
            onClick={() => mut.mutate()}
          >
            {mut.isPending ? "Submitting…" : isSuperAdmin ? "Archive" : "Submit request"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
