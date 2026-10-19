import { useEffect, useMemo, useRef, useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { ArrowLeft, Plus, Trash2, Save, GripVertical } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { NumberField } from "@/components/ui/number-field";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { OptionalSubjectCard } from "@/components/OptionalSubjectCard";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import type { ClassSubjectDetail, SubjectCategory } from "@/types/api";

const CATEGORY_LABEL: Record<SubjectCategory, string> = {
  academic: "Academic",
  co_curricular: "Co-curricular",
  grading: "Grading",
};

// Term select uses "both" as the sentinel for NULL (radix Select forbids an
// empty-string item value). Mapped back to null on save.
const TERM_OPTIONS: { value: string; label: string }[] = [
  { value: "both", label: "Both" },
  { value: "1", label: "Term 1" },
  { value: "2", label: "Term 2" },
];

interface DraftRow {
  // Local React key; `id` is the server component this row edits (null = new),
  // sent on save so a rename carries the component's existing marks with it.
  key: string;
  id: number | null;
  component_name: string;
  max_marks: string;
  order_index: string;
  term: string; // "both" | "1" | "2"
}

type Payload = { id: number | null; component_name: string; max_marks: number; order_index: number; term: number | null }[];
/** A save: what is sent, and the draft it was made from (to tell whether it was edited meanwhile). */
type SaveVars = { components: Payload; from: DraftRow[]; force?: boolean };

const draftFromServer = (rows: ClassSubjectDetail["components"]): DraftRow[] =>
  rows
    .slice()
    .sort((a, b) => a.order_index - b.order_index)
    .map((c, i) => ({
      key: `srv-${c.id}`,
      id: c.id,
      component_name: c.component_name,
      max_marks: String(c.max_marks),
      order_index: String(c.order_index || i + 1),
      term: c.term == null ? "both" : String(c.term),
    }));

/** True when the draft differs from the server's rows (ids included: a new exam has none yet). */
const rowsDiffer = (server: DraftRow[], draft: DraftRow[]): boolean =>
  server.length !== draft.length ||
  draft.some((d, i) => {
    const s = server[i];
    return !s
      || s.component_name !== d.component_name
      || s.max_marks !== d.max_marks
      || s.order_index !== d.order_index
      || s.term !== d.term
      || s.id !== d.id;
  });

const blankRow = (idx: number): DraftRow => ({
  key: `new-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`,
  id: null,
  component_name: "",
  max_marks: "0",
  order_index: String(idx),
  term: "both",
});

export default function ClassSubjectDetail() {
  const { t } = useTranslation();
  const { id } = useParams();
  const subjectId = Number(id);
  const qc = useQueryClient();
  const navigate = useNavigate();

  const [draft, setDraft] = useState<DraftRow[]>([]);
  // Set when the server refuses to delete components that already have marks.
  const [forcePrompt, setForcePrompt] = useState<{ message: string; vars: SaveVars } | null>(null);

  const subjectQ = useQuery<ClassSubjectDetail>({
    queryKey: ["class-subjects", subjectId],
    queryFn: () => api.get(`/class-subjects/${subjectId}`).then((r) => r.data),
    enabled: Number.isFinite(subjectId),
  });
  useSSE("class-subjects", [["class-subjects"]]);

  // The draft follows the server's rows (another super-admin's save arrives over SSE) while it
  // has no edits; one with edits keeps them. Replacing components doesn't touch the subject's
  // updated_at, so this watches the rows themselves.
  const synced = useRef<{ id: number; rows: DraftRow[] } | null>(null);
  useEffect(() => {
    const data = subjectQ.data;
    if (!data) return;
    const rows = draftFromServer(data.components);
    const prev = synced.current;
    synced.current = { id: data.id, rows };
    setDraft((d) => (!prev || prev.id !== data.id || !rowsDiffer(prev.rows, d) ? rows : d));
  }, [subjectQ.data]);

  const replace = useMutation({
    mutationFn: ({ components, force }: SaveVars) =>
      api
        .put<ClassSubjectDetail>(`/class-subjects/${subjectId}/components`, { components }, { params: force ? { force: true } : undefined })
        .then((r) => r.data),
    onSuccess: (saved, vars) => {
      toast("Exam components saved", "success");
      setForcePrompt(null);
      // Start again from the saved rows, so new exams carry their ids (a later rename then
      // edits them in place), unless the table was edited while saving.
      setDraft((d) => (d === vars.from ? draftFromServer(saved.components) : d));
      qc.setQueryData(["class-subjects", subjectId], saved);
      qc.invalidateQueries({ queryKey: ["class-subjects", subjectId] });
      qc.invalidateQueries({ queryKey: ["class-subjects"] });
      // Terms, max marks and names decide the results' totals and what report cards print.
      qc.invalidateQueries({ queryKey: ["results"] });
      qc.invalidateQueries({ queryKey: ["pdf-roster"] });
    },
    onError: (e, vars) => {
      const status = (e as { response?: { status?: number } })?.response?.status;
      const message = apiError(e);
      if (status === 409 && !vars.force && message.includes("already have marks")) {
        setForcePrompt({ message, vars });
        return;
      }
      toast(message, "error");
    },
  });

  // Per-scope max totals: a "Both" component counts in Term 1 and in Term 2.
  const totals = useMemo(() => {
    let term1 = 0, term2 = 0, annual = 0, both = 0;
    for (const r of draft) {
      const m = Number(r.max_marks) || 0;
      annual += m;
      if (r.term !== "2") term1 += m;
      if (r.term !== "1") term2 += m;
      if (r.term === "both" && m > 0) both += 1;
    }
    return { term1, term2, annual, both };
  }, [draft]);

  const isDirty = useMemo(
    () => !!subjectQ.data && rowsDiffer(draftFromServer(subjectQ.data.components), draft),
    [draft, subjectQ.data],
  );

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
    const cleaned: Payload = [];
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
        id: r.id,
        component_name: name,
        max_marks: marks,
        order_index: Number(r.order_index) || i + 1,
        term: r.term === "both" ? null : Number(r.term),
      });
    }
    replace.mutate({ components: cleaned, from: draft });
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
          {s.is_optional && (
            <Badge variant="info">{t("portal.classSubjects.optionalBadge", "Optional")}</Badge>
          )}
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
        below is the sum of all component max marks. <strong>Term</strong> controls
        which scope (Term 1 / Term 2 / Annual) a component rolls up into on the
        Results page and report cards — pick <em>Both</em> if it counts in either term.
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
                  <TableHead className="w-28">Term</TableHead>
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
                        max={1000}
                        integer
                        value={r.max_marks}
                        onChange={(v) => updateRow(r.key, { max_marks: v })}
                      />
                    </TableCell>
                    <TableCell>
                      <Select value={r.term} onValueChange={(v) => updateRow(r.key, { term: v })}>
                        <SelectTrigger className="h-9"><SelectValue /></SelectTrigger>
                        <SelectContent>
                          {TERM_OPTIONS.map((o) => <SelectItem key={o.value} value={o.value}>{o.label}</SelectItem>)}
                        </SelectContent>
                      </Select>
                    </TableCell>
                    <TableCell>
                      <NumberField
                        className="text-right"
                        min={0}
                        integer
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
                  <TableCell colSpan={3} className="text-right font-medium">
                    {t("portal.classSubjects.maxByScope", "Max marks · Term 1 / Term 2 / Annual")}
                  </TableCell>
                  <TableCell colSpan={4} className="font-bold">
                    {totals.term1} / {totals.term2} / {totals.annual}
                  </TableCell>
                </TableRow>
              </TableBody>
            </Table>
          )}
          {totals.both > 0 && (
            <p className="mt-3 text-xs text-amber-700">
              {t(
                "portal.classSubjects.bothWarning",
                "{{count}} components are set to “Both”, so they count in Term 1 and again in Term 2. Pick a single term unless that is intended.",
                { count: totals.both },
              )}
            </p>
          )}
          {isDirty && (
            <p className="mt-3 text-xs text-amber-700">
              You have unsaved changes. Save replaces the entire component list in one transaction.
            </p>
          )}
        </CardContent>
      </Card>

      {/* Who takes the subject: everyone, or (optional subject) only the students ticked there. */}
      <OptionalSubjectCard key={s.id} subject={s} />

      <Dialog open={!!forcePrompt} onOpenChange={(o) => { if (!o) setForcePrompt(null); }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{t("portal.classSubjects.forceDeleteTitle", "Delete components that have marks?")}</DialogTitle>
            <DialogDescription>{forcePrompt?.message}</DialogDescription>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            {t(
              "portal.classSubjects.forceDeleteBody",
              "Their marks stay in the database but no longer count in results or report cards. To rename a component instead, edit its name in place rather than deleting and re-adding it.",
            )}
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setForcePrompt(null)}>
              {t("portal.classSubjects.keepThem", "Keep them")}
            </Button>
            <Button
              variant="destructive"
              disabled={replace.isPending}
              onClick={() => forcePrompt && replace.mutate({ ...forcePrompt.vars, force: true })}
            >
              {t("portal.classSubjects.deleteAnyway", "Delete anyway")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
