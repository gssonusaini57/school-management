import { useEffect, useMemo, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, Plus, Trash2, Save, GripVertical } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { NumberField } from "@/components/ui/number-field";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import type { ClassSubjectDetail, SubjectCategory } from "@/types/api";

const CATEGORY_LABEL: Record<SubjectCategory, string> = {
  academic: "Academic",
  co_curricular: "Co-curricular",
  grading: "Grading",
};

interface DraftRow {
  // Local id used only for React keys while editing — server ids are stripped
  // on save because we PUT-replace the whole list.
  key: string;
  component_name: string;
  max_marks: string;
  order_index: string;
}

const draftFromServer = (rows: ClassSubjectDetail["components"]): DraftRow[] =>
  rows
    .slice()
    .sort((a, b) => a.order_index - b.order_index)
    .map((c, i) => ({
      key: `srv-${c.id}`,
      component_name: c.component_name,
      max_marks: String(c.max_marks),
      order_index: String(c.order_index || i + 1),
    }));

const blankRow = (idx: number): DraftRow => ({
  key: `new-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
  component_name: "",
  max_marks: "0",
  order_index: String(idx),
});

export default function ClassSubjectDetail() {
  const { id } = useParams();
  const subjectId = Number(id);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [draft, setDraft] = useState<DraftRow[]>([]);

  const subjectQ = useQuery<ClassSubjectDetail>({
    queryKey: ["class-subjects", subjectId],
    queryFn: () => api.get(`/class-subjects/${subjectId}`).then((r) => r.data),
    enabled: Number.isFinite(subjectId),
  });
  useSSE("class-subjects", [["class-subjects"]]);

  useEffect(() => {
    if (subjectQ.data) setDraft(draftFromServer(subjectQ.data.components));
  }, [subjectQ.data?.id, subjectQ.data?.updated_at]);

  const replace = useMutation({
    mutationFn: (components: { component_name: string; max_marks: number; order_index: number }[]) =>
      api.put(`/class-subjects/${subjectId}/components`, { components }),
    onSuccess: () => {
      toast("Exam components saved", "success");
      qc.invalidateQueries({ queryKey: ["class-subjects", subjectId] });
      qc.invalidateQueries({ queryKey: ["class-subjects"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const totalMax = useMemo(
    () => draft.reduce((acc, r) => acc + (Number(r.max_marks) || 0), 0),
    [draft],
  );

  const isDirty = useMemo(() => {
    if (!subjectQ.data) return false;
    const server = draftFromServer(subjectQ.data.components);
    if (server.length !== draft.length) return true;
    return draft.some((d, i) => {
      const s = server[i];
      if (!s) return true;
      return s.component_name !== d.component_name
        || s.max_marks !== d.max_marks
        || s.order_index !== d.order_index;
    });
  }, [draft, subjectQ.data]);

  const addRow = () => {
    setDraft((rows) => [...rows, blankRow(rows.length + 1)]);
  };

  const removeRow = (key: string) => {
    setDraft((rows) => rows.filter((r) => r.key !== key));
  };

  const updateRow = (key: string, patch: Partial<DraftRow>) => {
    setDraft((rows) => rows.map((r) => (r.key === key ? { ...r, ...patch } : r)));
  };

  const moveRow = (key: string, dir: -1 | 1) => {
    setDraft((rows) => {
      const idx = rows.findIndex((r) => r.key === key);
      if (idx < 0) return rows;
      const newIdx = idx + dir;
      if (newIdx < 0 || newIdx >= rows.length) return rows;
      const next = rows.slice();
      const [item] = next.splice(idx, 1);
      next.splice(newIdx, 0, item);
      return next.map((r, i) => ({ ...r, order_index: String(i + 1) }));
    });
  };

  const save = () => {
    const cleaned: { component_name: string; max_marks: number; order_index: number }[] = [];
    const seen = new Set<string>();
    for (let i = 0; i < draft.length; i++) {
      const r = draft[i];
      const name = r.component_name.trim();
      if (!name) {
        toast(`Row ${i + 1}: component name is required`, "error");
        return;
      }
      const lower = name.toLowerCase();
      if (seen.has(lower)) {
        toast(`Duplicate component name: ${name}`, "error");
        return;
      }
      seen.add(lower);
      const marks = Number(r.max_marks);
      if (Number.isNaN(marks) || marks < 0) {
        toast(`Row ${i + 1}: max marks must be a non-negative number`, "error");
        return;
      }
      cleaned.push({
        component_name: name,
        max_marks: marks,
        order_index: Number(r.order_index) || i + 1,
      });
    }
    replace.mutate(cleaned);
  };

  if (subjectQ.isLoading) {
    return <p className="text-sm text-muted-foreground">Loading…</p>;
  }
  if (subjectQ.isError || !subjectQ.data) {
    return (
      <div className="space-y-3">
        <Link to="/class-subjects">
          <Button variant="ghost" size="sm"><ArrowLeft className="h-4 w-4" /> Back</Button>
        </Link>
        <p className="text-sm text-destructive">Subject not found.</p>
      </div>
    );
  }

  const s = subjectQ.data;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => navigate("/class-subjects")}>
            <ArrowLeft className="h-4 w-4" /> All subjects
          </Button>
          <h1 className="font-display text-heading-lg text-deep-indigo">
            {s.class_name} — {s.subject_name}
          </h1>
          <Badge variant={s.category === "academic" ? "default" : s.category === "co_curricular" ? "secondary" : "outline"}>
            {CATEGORY_LABEL[s.category]}
          </Badge>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" onClick={addRow}>
            <Plus className="h-4 w-4" /> Add component
          </Button>
          <Button onClick={save} disabled={!isDirty || replace.isPending}>
            <Save className="h-4 w-4" /> {replace.isPending ? "Saving…" : isDirty ? "Save changes" : "Saved"}
          </Button>
        </div>
      </div>

      <p className="text-sm text-muted-foreground max-w-3xl">
        Define every test or component that contributes to {s.subject_name}'s total
        (e.g. <code>P.T. First / 35</code>, <code>Semester First / 80</code>,
        <code> Semester First — Practical / 10</code>). The total max marks shown
        below is the sum of all component max marks.
      </p>

      <Card>
        <CardContent className="pt-6">
          {draft.length === 0 ? (
            <div className="text-sm text-muted-foreground py-10 text-center space-y-2">
              <p>No components yet.</p>
              <Button variant="outline" onClick={addRow}>
                <Plus className="h-4 w-4" /> Add the first component
              </Button>
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16"></TableHead>
                  <TableHead className="w-16 text-right">#</TableHead>
                  <TableHead>Component name</TableHead>
                  <TableHead className="w-32 text-right">Max marks</TableHead>
                  <TableHead className="w-20 text-right">Order</TableHead>
                  <TableHead className="w-20 text-right"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {draft.map((r, i) => (
                  <TableRow key={r.key}>
                    <TableCell>
                      <div className="flex flex-col">
                        <Button
                          size="icon" variant="ghost"
                          className="h-5 w-5"
                          aria-label="Move up"
                          disabled={i === 0}
                          onClick={() => moveRow(r.key, -1)}
                        >
                          <GripVertical className="h-3 w-3 -rotate-90" />
                        </Button>
                        <Button
                          size="icon" variant="ghost"
                          className="h-5 w-5"
                          aria-label="Move down"
                          disabled={i === draft.length - 1}
                          onClick={() => moveRow(r.key, 1)}
                        >
                          <GripVertical className="h-3 w-3 rotate-90" />
                        </Button>
                      </div>
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">{i + 1}</TableCell>
                    <TableCell>
                      <Input
                        value={r.component_name}
                        onChange={(e) => updateRow(r.key, { component_name: e.target.value })}
                        placeholder="e.g. P.T. First"
                      />
                    </TableCell>
                    <TableCell>
                      <NumberField
                        className="text-right"
                        min={0}
                        value={r.max_marks}
                        onChange={(v) => updateRow(r.key, { max_marks: v })}
                      />
                    </TableCell>
                    <TableCell>
                      <NumberField
                        className="text-right"
                        min={0}
                        value={r.order_index}
                        onChange={(v) => updateRow(r.key, { order_index: v })}
                      />
                    </TableCell>
                    <TableCell className="text-right">
                      <Button size="icon" variant="ghost" onClick={() => removeRow(r.key)} aria-label="Remove component">
                        <Trash2 className="h-4 w-4 text-destructive" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                <TableRow className="bg-cream/40">
                  <TableCell colSpan={3} className="text-right font-medium">Total max marks</TableCell>
                  <TableCell className="text-right font-bold">{totalMax}</TableCell>
                  <TableCell colSpan={2}></TableCell>
                </TableRow>
              </TableBody>
            </Table>
          )}
          {isDirty && (
            <p className="mt-3 text-xs text-amber-700">
              You have unsaved changes. Save replaces the entire component list in one transaction.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
