import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, FileSpreadsheet, Save, X, ChevronRight, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { NumberField } from "@/components/ui/number-field";
import { CLASSES } from "@/lib/utils";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { CLASS_SUBJECTS_TEMPLATE } from "@/lib/templates";
import type { ClassSubject, SubjectCategory } from "@/types/api";

interface FormState {
  class_name: string;
  subject_name: string;
  subject_name_pa: string;
  category: SubjectCategory;
  order_index: string;
}

const emptyForm = (cls = ""): FormState => ({
  class_name: cls,
  subject_name: "",
  subject_name_pa: "",
  category: "academic",
  order_index: "0",
});

const CATEGORY_LABEL: Record<SubjectCategory, string> = {
  academic: "Academic",
  co_curricular: "Co-curricular",
  grading: "Grading",
};

const CATEGORY_VARIANT: Record<SubjectCategory, "default" | "secondary" | "outline"> = {
  academic: "default",
  co_curricular: "secondary",
  grading: "outline",
};

export default function ClassSubjects() {
  const qc = useQueryClient();
  const [filterCls, setFilterCls] = useState<string>("");
  const [addOpen, setAddOpen] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [seedConfirmOpen, setSeedConfirmOpen] = useState(false);
  const [editing, setEditing] = useState<ClassSubject | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<ClassSubject | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm());

  const { data = [] } = useQuery<ClassSubject[]>({
    queryKey: ["class-subjects"],
    queryFn: () => api.get("/class-subjects").then((r) => r.data),
  });
  useSSE("class-subjects", [["class-subjects"]]);

  const rows = useMemo(() => {
    const filtered = filterCls ? data.filter((r) => r.class_name === filterCls) : data;
    return filtered.slice().sort((a, b) => {
      if (a.class_name !== b.class_name) return a.class_name.localeCompare(b.class_name);
      if (a.order_index !== b.order_index) return a.order_index - b.order_index;
      return a.subject_name.localeCompare(b.subject_name);
    });
  }, [data, filterCls]);

  const create = useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post("/class-subjects", body),
    onSuccess: () => {
      toast("Subject added", "success");
      setAddOpen(false);
      setForm(emptyForm(filterCls));
      qc.invalidateQueries({ queryKey: ["class-subjects"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const update = useMutation({
    mutationFn: ({ id, body }: { id: number; body: Record<string, unknown> }) =>
      api.patch(`/class-subjects/${id}`, body),
    onSuccess: () => {
      toast("Subject updated", "success");
      setEditing(null);
      qc.invalidateQueries({ queryKey: ["class-subjects"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.delete(`/class-subjects/${id}`),
    onSuccess: () => {
      toast("Subject removed", "success");
      setDeleteTarget(null);
      qc.invalidateQueries({ queryKey: ["class-subjects"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const seed = useMutation({
    mutationFn: () => api.post("/class-subjects/seed-defaults"),
    onSuccess: (r: any) => {
      const { subjects = 0, components = 0 } = r.data ?? {};
      toast(`Seeded ${subjects} subjects with ${components} components`, "success");
      setSeedConfirmOpen(false);
      qc.invalidateQueries({ queryKey: ["class-subjects"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const openAdd = () => {
    setForm(emptyForm(filterCls));
    setAddOpen(true);
  };

  const submitCreate = () => {
    if (!form.class_name || !form.subject_name.trim()) {
      toast("Class and subject name are required", "error");
      return;
    }
    create.mutate({
      class_name: form.class_name,
      subject_name: form.subject_name.trim(),
      subject_name_pa: form.subject_name_pa.trim() || null,
      category: form.category,
      order_index: Number(form.order_index) || 0,
    });
  };

  const isEmpty = data.length === 0;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">Class Subjects</h1>
        <div className="flex items-center gap-2">
          {isEmpty && (
            <Button variant="default" onClick={() => setSeedConfirmOpen(true)}>
              <Sparkles className="h-4 w-4" /> Seed KIS default pattern
            </Button>
          )}
          <Button onClick={openAdd}>
            <Plus className="h-4 w-4" /> Add subject
          </Button>
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <FileSpreadsheet className="h-4 w-4" /> Bulk import
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground max-w-3xl">
        Per-class subject roster. After adding a subject, open it to configure
        its exam components (P.T. First, Semester First, Practical, etc.) and
        the max marks for each. Only super-admins can edit this master.
      </p>

      <BulkImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bulk import subjects"
        description="One row per (class × subject). Required: class_name, subject_name. Optional: subject_name_pa, category (academic | co_curricular | grading — default academic), order_index. Components are managed per-subject after import."
        templateCsv={CLASS_SUBJECTS_TEMPLATE}
        templateFilename="class-subjects-template.csv"
        uploadPath="/class-subjects/bulk-import"
        onSuccess={() => qc.invalidateQueries({ queryKey: ["class-subjects"] })}
      />

      <Card>
        <CardContent className="pt-6 space-y-4">
          <div className="flex items-end gap-3 flex-wrap">
            <div className="space-y-1.5">
              <Label>Filter by class</Label>
              <Select value={filterCls || "__all__"} onValueChange={(v) => setFilterCls(v === "__all__" ? "" : v)}>
                <SelectTrigger className="w-48"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="__all__">All classes</SelectItem>
                  {CLASSES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="text-sm text-muted-foreground pb-2">
              {rows.length} subject{rows.length === 1 ? "" : "s"} {filterCls ? `in ${filterCls}` : "across all classes"}
            </div>
          </div>

          {!rows.length ? (
            <div className="text-sm text-muted-foreground py-12 text-center space-y-2">
              <p>No subjects yet.</p>
              {isEmpty && (
                <p>
                  Click <strong>Seed KIS default pattern</strong> to populate all classes
                  (Nursery → 12th) with the exam pattern from the school's exam-pattern
                  sheet, or add subjects manually.
                </p>
              )}
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-24">Class</TableHead>
                  <TableHead>Subject</TableHead>
                  <TableHead>Subject (ਪੰਜਾਬੀ)</TableHead>
                  <TableHead className="w-32">Category</TableHead>
                  <TableHead className="w-20 text-right">Order</TableHead>
                  <TableHead className="w-40 text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r) => (
                  <TableRow key={r.id}>
                    <TableCell className="font-medium">{r.class_name}</TableCell>
                    <TableCell>
                      <Link to={`/class-subjects/${r.id}`} className="hover:underline text-khalsa-blue font-medium">
                        {r.subject_name}
                      </Link>
                    </TableCell>
                    <TableCell className="text-muted-foreground font-display">
                      {r.subject_name_pa ?? "—"}
                    </TableCell>
                    <TableCell>
                      <Badge variant={CATEGORY_VARIANT[r.category]}>{CATEGORY_LABEL[r.category]}</Badge>
                    </TableCell>
                    <TableCell className="text-right">{r.order_index}</TableCell>
                    <TableCell className="text-right">
                      <Link to={`/class-subjects/${r.id}`}>
                        <Button size="sm" variant="ghost">
                          Components <ChevronRight className="h-4 w-4" />
                        </Button>
                      </Link>
                      <Button size="icon" variant="ghost" onClick={() => setEditing(r)} aria-label="Edit subject">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="ghost" onClick={() => setDeleteTarget(r)} aria-label="Delete subject">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Add dialog */}
      <Dialog open={addOpen} onOpenChange={setAddOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add subject</DialogTitle>
            <DialogDescription>
              Add a subject to a class's roster. Configure its exam components after saving.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div className="space-y-1.5">
                <Label>Class</Label>
                <Select value={form.class_name} onValueChange={(v) => setForm({ ...form, class_name: v })}>
                  <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>{CLASSES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Category</Label>
                <Select value={form.category} onValueChange={(v) => setForm({ ...form, category: v as SubjectCategory })}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="academic">Academic — scored</SelectItem>
                    <SelectItem value="co_curricular">Co-curricular — scored separately</SelectItem>
                    <SelectItem value="grading">Grading — letter grade only</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Subject name</Label>
              <Input
                value={form.subject_name}
                onChange={(e) => setForm({ ...form, subject_name: e.target.value })}
                placeholder="e.g. Mathematics"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Subject name (Punjabi) <span className="text-muted-foreground">— optional</span></Label>
              <Input
                value={form.subject_name_pa}
                onChange={(e) => setForm({ ...form, subject_name_pa: e.target.value })}
                placeholder="e.g. ਗਣਿਤ"
              />
            </div>
            <div className="space-y-1.5">
              <Label>Display order <span className="text-muted-foreground">— lower = first</span></Label>
              <NumberField
                min={0}
                value={form.order_index}
                onChange={(v) => setForm({ ...form, order_index: v })}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
            <Button onClick={submitCreate} disabled={create.isPending}>
              <Save className="h-4 w-4" /> {create.isPending ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit dialog */}
      <Dialog open={!!editing} onOpenChange={(o) => !o && setEditing(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit subject</DialogTitle>
            <DialogDescription>{editing && `${editing.class_name} — ${editing.subject_name}`}</DialogDescription>
          </DialogHeader>
          {editing && (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <Label>Subject name</Label>
                <Input
                  value={editing.subject_name}
                  onChange={(e) => setEditing({ ...editing, subject_name: e.target.value })}
                />
              </div>
              <div className="space-y-1.5">
                <Label>Subject name (Punjabi)</Label>
                <Input
                  value={editing.subject_name_pa ?? ""}
                  onChange={(e) => setEditing({ ...editing, subject_name_pa: e.target.value })}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <Label>Category</Label>
                  <Select
                    value={editing.category}
                    onValueChange={(v) => setEditing({ ...editing, category: v as SubjectCategory })}
                  >
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="academic">Academic</SelectItem>
                      <SelectItem value="co_curricular">Co-curricular</SelectItem>
                      <SelectItem value="grading">Grading</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5">
                  <Label>Display order</Label>
                  <NumberField
                    min={0}
                    value={String(editing.order_index)}
                    onChange={(v) => setEditing({ ...editing, order_index: v === "" ? 0 : Number(v) })}
                  />
                </div>
              </div>
            </div>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditing(null)}>
              <X className="h-4 w-4" /> Cancel
            </Button>
            <Button
              disabled={update.isPending}
              onClick={() => editing && update.mutate({
                id: editing.id,
                body: {
                  subject_name: editing.subject_name,
                  subject_name_pa: editing.subject_name_pa,
                  category: editing.category,
                  order_index: editing.order_index,
                },
              })}
            >
              <Save className="h-4 w-4" /> {update.isPending ? "Saving…" : "Save changes"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete confirm */}
      <Dialog open={!!deleteTarget} onOpenChange={(o) => !o && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Remove subject?</DialogTitle>
            <DialogDescription>
              {deleteTarget && (
                <>
                  {deleteTarget.subject_name} ({deleteTarget.class_name}) will be removed from the
                  master, along with all its exam components. Existing marks rows are NOT deleted.
                </>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button
              variant="destructive"
              disabled={del.isPending}
              onClick={() => deleteTarget && del.mutate(deleteTarget.id)}
            >
              <Trash2 className="h-4 w-4" /> {del.isPending ? "Removing…" : "Remove"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Seed confirm */}
      <Dialog open={seedConfirmOpen} onOpenChange={setSeedConfirmOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Seed KIS default exam pattern?</DialogTitle>
            <DialogDescription>
              This will create the full subject + exam-component master across all classes
              (Nursery, L.K.G, U.K.G, 1st–12th) based on the school's exam-pattern sheet
              (P.T. First/Second 35, Semester First 80, etc., with practical splits for
              Maths/Science in classes 6–10). You'll be able to edit every value afterward.
              <br /><br />
              Seeding only works on an empty master.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setSeedConfirmOpen(false)}>Cancel</Button>
            <Button onClick={() => seed.mutate()} disabled={seed.isPending}>
              <Sparkles className="h-4 w-4" /> {seed.isPending ? "Seeding…" : "Seed defaults"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
