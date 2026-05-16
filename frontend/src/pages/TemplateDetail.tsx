import { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft, FileDown, RefreshCw, Save, Trash2, Plus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { downloadCachedPdf } from "@/lib/pdf";
import type {
  PdfTemplate, PdfStudentDataRow, PdfStudentRosterRow, PdfRenderResultRow,
} from "@/types/api";

export default function TemplateDetail() {
  const { id: idStr } = useParams<{ id: string }>();
  const id = Number(idStr);
  const nav = useNavigate();

  const tpl = useQuery<PdfTemplate>({
    queryKey: ["pdf-template", id],
    queryFn: () => api.get(`/pdf/templates/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  if (tpl.isLoading) return <p className="p-6 text-muted-foreground">Loading template…</p>;
  if (!tpl.data) return (
    <div className="p-6 space-y-3">
      <p className="text-muted-foreground">Template not found.</p>
      <Button variant="outline" onClick={() => nav("/templates")}><ArrowLeft className="h-4 w-4" /> Back</Button>
    </div>
  );

  const t = tpl.data;
  return (
    <div className="space-y-4">
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <Button variant="ghost" size="sm" onClick={() => nav("/templates")}><ArrowLeft className="h-4 w-4" /> All templates</Button>
          <h1 className="font-display text-heading-lg text-deep-indigo mt-1">
            {t.kind === "report-card" ? "Report Card" : "PSEB Admit Card"} · <Badge variant="info" className="ml-1">{t.class_name}</Badge>
          </h1>
          <p className="text-sm text-muted-foreground">Session {t.session}{t.term ? ` · ${t.term}` : ""} · v{t.version}</p>
        </div>
      </div>

      <TemplateForm template={t} />
      <StudentDataSpreadsheet template={t} />
      <BulkRenderPanel template={t} />
    </div>
  );
}

// ─── Section 1: Class-level template form ────────────────────────────────

function TemplateForm({ template }: { template: PdfTemplate }) {
  const qc = useQueryClient();
  const [data, setData] = useState<Record<string, unknown>>(template.data);

  useEffect(() => { setData(template.data); }, [template.id, template.version]);

  const save = useMutation({
    mutationFn: () => api.patch<PdfTemplate>(`/pdf/templates/${template.id}`, { data }),
    onSuccess: () => {
      toast("Template saved · cache invalidated", "success");
      qc.invalidateQueries({ queryKey: ["pdf-template", template.id] });
      qc.invalidateQueries({ queryKey: ["pdf-templates"] });
      qc.invalidateQueries({ queryKey: ["pdf-roster", template.id] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Class-level template</span>
          <Button onClick={() => save.mutate()} disabled={save.isPending}>
            <Save className="h-4 w-4" /> {save.isPending ? "Saving…" : "Save (bumps version → invalidates cache)"}
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent>
        {template.kind === "report-card"
          ? <ReportCardTemplateForm data={data} setData={setData} />
          : <PsebTemplateForm data={data} setData={setData} />}
      </CardContent>
    </Card>
  );
}

function ReportCardTemplateForm({
  data, setData,
}: { data: Record<string, unknown>; setData: (d: Record<string, unknown>) => void }) {
  const sigs = (data.signatures as Record<string, string> | undefined) ?? {};
  const heads = (data.coScholasticHeads as Array<{ name: { en: string; pa: string } }>) ?? [];

  const updateSig = (k: string, v: string) =>
    setData({ ...data, signatures: { ...sigs, [k]: v } });

  const setHeads = (next: typeof heads) => setData({ ...data, coScholasticHeads: next });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="space-y-1.5"><Label>Class teacher</Label>
          <Input value={sigs.classTeacher ?? ""} onChange={(e) => updateSig("classTeacher", e.target.value)} />
        </div>
        <div className="space-y-1.5"><Label>Examination in-charge</Label>
          <Input value={sigs.examIncharge ?? ""} onChange={(e) => updateSig("examIncharge", e.target.value)} />
        </div>
        <div className="space-y-1.5"><Label>Principal</Label>
          <Input value={sigs.principal ?? ""} onChange={(e) => updateSig("principal", e.target.value)} />
        </div>
      </div>

      <div className="space-y-1.5"><Label>Default promotion text</Label>
        <Input value={(data.promotionDefault as string) ?? ""} onChange={(e) => setData({ ...data, promotionDefault: e.target.value })} placeholder="Promoted to Class IX with distinction" />
      </div>

      <div className="space-y-2 border-t pt-3">
        <div className="flex items-center justify-between">
          <Label className="font-semibold">Co-scholastic heads (column labels for the per-student table)</Label>
          <Button type="button" size="sm" variant="outline" onClick={() =>
            setHeads([...heads, { name: { en: "", pa: "" } }])
          }><Plus className="h-4 w-4" /> Add head</Button>
        </div>
        {heads.length === 0 && <p className="text-xs text-muted-foreground">Add one or more headings (e.g. "Punjabi Culture", "Art &amp; Craft"). Each becomes a column the teacher fills in per student below.</p>}
        {heads.map((h, i) => (
          <div key={i} className="flex gap-2 items-end">
            <div className="flex-1 space-y-1"><Label className="text-xs">Heading (English)</Label>
              <Input value={h.name.en} onChange={(e) => {
                const next = [...heads]; next[i] = { name: { ...h.name, en: e.target.value } }; setHeads(next);
              }} />
            </div>
            <div className="flex-1 space-y-1"><Label className="text-xs">Heading (ਪੰਜਾਬੀ)</Label>
              <Input value={h.name.pa} onChange={(e) => {
                const next = [...heads]; next[i] = { name: { ...h.name, pa: e.target.value } }; setHeads(next);
              }} className="font-gurmukhi" />
            </div>
            <Button type="button" size="icon" variant="ghost" className="text-red-600" onClick={() => setHeads(heads.filter((_, j) => j !== i))}>
              <Trash2 className="h-4 w-4" />
            </Button>
          </div>
        ))}
      </div>
    </div>
  );
}

function PsebTemplateForm({
  data, setData,
}: { data: Record<string, unknown>; setData: (d: Record<string, unknown>) => void }) {
  const centre = (data.centre as Record<string, unknown>) ?? {};
  const centreName = (centre.name as { en?: string; pa?: string }) ?? {};
  const examTime = (data.examTime as { en?: string; pa?: string }) ?? {};
  const range = (data.practicalDateRange as { from?: string; to?: string } | null) ?? null;
  const sheet = (data.dateSheet as Array<{ subCode: string; subject: { en: string; pa: string }; theoryDate: string; practical: string }>) ?? [];
  const instructions = (data.instructions as Array<{ en: string; pa: string }>) ?? [];

  const setCentre = (k: string, v: unknown) => setData({ ...data, centre: { ...centre, [k]: v } });
  const setCentreName = (k: "en" | "pa", v: string) => setCentre("name", { ...centreName, [k]: v });
  const setSheet = (next: typeof sheet) => setData({ ...data, dateSheet: next });
  const setIns = (next: typeof instructions) => setData({ ...data, instructions: next });

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-3 gap-2">
        <div className="space-y-1.5"><Label>School code</Label>
          <Input value={(data.schoolCode as string) ?? ""} onChange={(e) => setData({ ...data, schoolCode: e.target.value })} />
        </div>
        <div className="space-y-1.5"><Label>Exam name</Label>
          <Input value={(data.examName as string) ?? ""} onChange={(e) => setData({ ...data, examName: e.target.value })} placeholder="PSEB Class X — Annual 2026" />
        </div>
        <div />
      </div>

      <div className="grid grid-cols-4 gap-2">
        <div className="space-y-1.5"><Label>Centre code</Label><Input value={(centre.code as string) ?? ""} onChange={(e) => setCentre("code", e.target.value)} /></div>
        <div className="space-y-1.5"><Label>Centre school code</Label><Input value={(centre.schoolCode as string) ?? ""} onChange={(e) => setCentre("schoolCode", e.target.value)} /></div>
        <div className="space-y-1.5"><Label>District</Label><Input value={(centre.district as string) ?? ""} onChange={(e) => setCentre("district", e.target.value)} /></div>
        <div className="space-y-1.5"><Label>Set</Label><Input value={(centre.set as string) ?? ""} onChange={(e) => setCentre("set", e.target.value)} /></div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1.5"><Label>Centre name (English)</Label><Input value={centreName.en ?? ""} onChange={(e) => setCentreName("en", e.target.value)} /></div>
        <div className="space-y-1.5"><Label>Centre name (ਪੰਜਾਬੀ)</Label><Input value={centreName.pa ?? ""} onChange={(e) => setCentreName("pa", e.target.value)} className="font-gurmukhi" /></div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1.5"><Label>Exam time (English)</Label><Input value={examTime.en ?? ""} onChange={(e) => setData({ ...data, examTime: { ...examTime, en: e.target.value } })} /></div>
        <div className="space-y-1.5"><Label>Exam time (ਪੰਜਾਬੀ)</Label><Input value={examTime.pa ?? ""} onChange={(e) => setData({ ...data, examTime: { ...examTime, pa: e.target.value } })} className="font-gurmukhi" /></div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1.5"><Label>Practical from (DD-MM-YYYY)</Label><Input value={range?.from ?? ""} onChange={(e) => setData({ ...data, practicalDateRange: { ...(range || { from: "", to: "" }), from: e.target.value } })} /></div>
        <div className="space-y-1.5"><Label>Practical to (DD-MM-YYYY)</Label><Input value={range?.to ?? ""} onChange={(e) => setData({ ...data, practicalDateRange: { ...(range || { from: "", to: "" }), to: e.target.value } })} /></div>
      </div>

      <div className="space-y-2 border-t pt-3">
        <div className="flex items-center justify-between">
          <Label className="font-semibold">Date sheet</Label>
          <Button type="button" size="sm" variant="outline" onClick={() =>
            setSheet([...sheet, { subCode: "", subject: { en: "", pa: "" }, theoryDate: "", practical: "No" }])
          }><Plus className="h-4 w-4" /> Add row</Button>
        </div>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-20">Code</TableHead>
              <TableHead>Subject (English)</TableHead>
              <TableHead>Subject (ਪੰਜਾਬੀ)</TableHead>
              <TableHead className="w-32">Theory (DD-MM-YYYY)</TableHead>
              <TableHead className="w-24">Practical</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sheet.map((r, i) => (
              <TableRow key={i}>
                <TableCell><Input value={r.subCode} onChange={(e) => { const next = [...sheet]; next[i] = { ...r, subCode: e.target.value }; setSheet(next); }} className="h-8" /></TableCell>
                <TableCell><Input value={r.subject.en} onChange={(e) => { const next = [...sheet]; next[i] = { ...r, subject: { ...r.subject, en: e.target.value } }; setSheet(next); }} className="h-8" /></TableCell>
                <TableCell><Input value={r.subject.pa} onChange={(e) => { const next = [...sheet]; next[i] = { ...r, subject: { ...r.subject, pa: e.target.value } }; setSheet(next); }} className="h-8 font-gurmukhi" /></TableCell>
                <TableCell><Input value={r.theoryDate} onChange={(e) => { const next = [...sheet]; next[i] = { ...r, theoryDate: e.target.value }; setSheet(next); }} className="h-8" /></TableCell>
                <TableCell>
                  <Select value={r.practical} onValueChange={(v) => { const next = [...sheet]; next[i] = { ...r, practical: v }; setSheet(next); }}>
                    <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                    <SelectContent><SelectItem value="Yes">Yes</SelectItem><SelectItem value="No">No</SelectItem></SelectContent>
                  </Select>
                </TableCell>
                <TableCell><Button size="icon" variant="ghost" className="text-red-600" onClick={() => setSheet(sheet.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button></TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>

      <div className="space-y-2 border-t pt-3">
        <div className="flex items-center justify-between">
          <Label className="font-semibold">Instructions</Label>
          <Button type="button" size="sm" variant="outline" onClick={() => setIns([...instructions, { en: "", pa: "" }])}><Plus className="h-4 w-4" /> Add</Button>
        </div>
        {instructions.map((ins, i) => (
          <div key={i} className="flex gap-2 items-start">
            <Textarea value={ins.en} onChange={(e) => { const next = [...instructions]; next[i] = { ...ins, en: e.target.value }; setIns(next); }} rows={1} placeholder="English instruction" className="flex-1" />
            <Textarea value={ins.pa} onChange={(e) => { const next = [...instructions]; next[i] = { ...ins, pa: e.target.value }; setIns(next); }} rows={1} placeholder="Punjabi" className="flex-1 font-gurmukhi" />
            <Button size="icon" variant="ghost" className="text-red-600" onClick={() => setIns(instructions.filter((_, j) => j !== i))}><Trash2 className="h-4 w-4" /></Button>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Section 2: Per-student data spreadsheet ─────────────────────────────

function StudentDataSpreadsheet({ template }: { template: PdfTemplate }) {
  const qc = useQueryClient();

  const roster = useQuery<PdfStudentRosterRow[]>({
    queryKey: ["pdf-roster", template.id],
    queryFn: () => api.get(`/pdf/templates/${template.id}/students`).then((r) => r.data),
  });
  const dataQ = useQuery<PdfStudentDataRow[]>({
    queryKey: ["pdf-student-data", template.id],
    queryFn: () => api.get(`/pdf/templates/${template.id}/student-data`).then((r) => r.data),
  });

  const initialMap = useMemo(() => {
    const m = new Map<number, Record<string, unknown>>();
    (dataQ.data ?? []).forEach((r) => m.set(r.student_id, r.data));
    return m;
  }, [dataQ.data]);

  const [edits, setEdits] = useState<Map<number, Record<string, unknown>>>(new Map());
  useEffect(() => { setEdits(new Map()); }, [initialMap]);

  const valueOf = (sid: number) => edits.get(sid) ?? initialMap.get(sid) ?? {};

  const setField = (sid: number, key: string, value: unknown) => {
    const next = new Map(edits);
    const current = { ...(next.get(sid) ?? initialMap.get(sid) ?? {}) };
    current[key] = value;
    next.set(sid, current);
    setEdits(next);
  };

  const save = useMutation({
    mutationFn: () => {
      const entries = [...edits.entries()].map(([student_id, data]) => ({ student_id, data }));
      return api.put(`/pdf/templates/${template.id}/student-data`, { entries });
    },
    onSuccess: () => {
      toast("Saved", "success");
      qc.invalidateQueries({ queryKey: ["pdf-student-data", template.id] });
      qc.invalidateQueries({ queryKey: ["pdf-roster", template.id] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const heads = ((template.data as Record<string, unknown>).coScholasticHeads as
    Array<{ name: { en: string; pa: string } }> | undefined) ?? [];

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Per-student data {edits.size > 0 && <Badge variant="warning" className="ml-2">{edits.size} unsaved</Badge>}</span>
          <Button onClick={() => save.mutate()} disabled={save.isPending || edits.size === 0}>
            <Save className="h-4 w-4" /> {save.isPending ? "Saving…" : `Save ${edits.size || ""} changes`}
          </Button>
        </CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        {roster.isLoading ? <p className="text-muted-foreground text-sm">Loading…</p>
          : !roster.data?.length ? <p className="text-muted-foreground text-sm">No students in class {template.class_name}.</p>
          : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead>
                  <TableHead>Student</TableHead>
                  {template.kind === "pseb-admit-card" ? (
                    <>
                      <TableHead>Roll No</TableHead>
                      <TableHead>Reg No</TableHead>
                      <TableHead>Category</TableHead>
                      <TableHead>Differently abled</TableHead>
                    </>
                  ) : (
                    <>
                      {heads.map((h, i) => <TableHead key={i}>{h.name.en || `Head ${i + 1}`}</TableHead>)}
                      <TableHead>Att %</TableHead>
                      <TableHead>Rank</TableHead>
                      <TableHead>Class size</TableHead>
                      <TableHead>Remarks (EN)</TableHead>
                    </>
                  )}
                </TableRow>
              </TableHeader>
              <TableBody>
                {(roster.data ?? []).map((s, i) => {
                  const d = valueOf(s.id);
                  if (template.kind === "pseb-admit-card") {
                    return (
                      <TableRow key={s.id}>
                        <TableCell>{i + 1}</TableCell>
                        <TableCell className="font-medium">{s.name}</TableCell>
                        <TableCell><Input className="h-8" value={(d.rollNo as string) ?? ""} onChange={(e) => setField(s.id, "rollNo", e.target.value)} /></TableCell>
                        <TableCell><Input className="h-8" value={(d.regNo as string) ?? ""} onChange={(e) => setField(s.id, "regNo", e.target.value)} /></TableCell>
                        <TableCell>
                          <Select value={(d.category as string) ?? "Regular"} onValueChange={(v) => setField(s.id, "category", v)}>
                            <SelectTrigger className="h-8"><SelectValue /></SelectTrigger>
                            <SelectContent>
                              <SelectItem value="Regular">Regular</SelectItem>
                              <SelectItem value="Repeater">Repeater</SelectItem>
                              <SelectItem value="Open">Open</SelectItem>
                            </SelectContent>
                          </Select>
                        </TableCell>
                        <TableCell><Input className="h-8" value={(d.differentlyAbled as string) ?? "N.A."} onChange={(e) => setField(s.id, "differentlyAbled", e.target.value)} /></TableCell>
                      </TableRow>
                    );
                  }
                  // report-card
                  const grades = (d.coScholasticGrades as Array<{ head: string; grade: string }>) ?? [];
                  const gradeFor = (head: string) => grades.find((g) => g.head === head)?.grade ?? "";
                  const setGrade = (head: string, grade: string) => {
                    const others = grades.filter((g) => g.head !== head);
                    setField(s.id, "coScholasticGrades", grade ? [...others, { head, grade }] : others);
                  };
                  return (
                    <TableRow key={s.id}>
                      <TableCell>{i + 1}</TableCell>
                      <TableCell className="font-medium">{s.name}</TableCell>
                      {heads.map((h, j) => (
                        <TableCell key={j}>
                          <Input className="h-8 w-16" value={gradeFor(h.name.en)} onChange={(e) => setGrade(h.name.en, e.target.value)} placeholder="A1" />
                        </TableCell>
                      ))}
                      <TableCell><Input type="number" className="h-8 w-20" value={(d.attendancePct as number | string) ?? ""} onChange={(e) => setField(s.id, "attendancePct", e.target.value === "" ? null : Number(e.target.value))} /></TableCell>
                      <TableCell><Input type="number" className="h-8 w-16" value={(d.rank as number | string) ?? ""} onChange={(e) => setField(s.id, "rank", e.target.value === "" ? null : Number(e.target.value))} /></TableCell>
                      <TableCell><Input type="number" className="h-8 w-20" value={(d.classSize as number | string) ?? ""} onChange={(e) => setField(s.id, "classSize", e.target.value === "" ? null : Number(e.target.value))} /></TableCell>
                      <TableCell>
                        <Input className="h-8 min-w-48"
                          value={(d.remarks as { en?: string } | undefined)?.en ?? ""}
                          onChange={(e) => setField(s.id, "remarks", { en: e.target.value, pa: (d.remarks as { pa?: string } | undefined)?.pa ?? e.target.value })}
                          placeholder="Excellent term" />
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )
        }
      </CardContent>
    </Card>
  );
}

// ─── Section 3: Bulk render panel ────────────────────────────────────────

function BulkRenderPanel({ template }: { template: PdfTemplate }) {
  const qc = useQueryClient();
  const roster = useQuery<PdfStudentRosterRow[]>({
    queryKey: ["pdf-roster", template.id],
    queryFn: () => api.get(`/pdf/templates/${template.id}/students`).then((r) => r.data),
  });

  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [force, setForce] = useState(false);
  const [results, setResults] = useState<Map<number, PdfRenderResultRow>>(new Map());

  const all = roster.data ?? [];
  const allChecked = all.length > 0 && selected.size === all.length;
  const toggle = (id: number) => {
    const n = new Set(selected); n.has(id) ? n.delete(id) : n.add(id); setSelected(n);
  };
  const toggleAll = () => setSelected(allChecked ? new Set() : new Set(all.map((s) => s.id)));

  const render = useMutation({
    mutationFn: () => api.post(`/pdf/templates/${template.id}/render`,
      { student_ids: [...selected], force },
      { timeout: 5 * 60_000 },
    ),
    onSuccess: ({ data }) => {
      const m = new Map<number, PdfRenderResultRow>();
      for (const r of data.results as PdfRenderResultRow[]) m.set(r.student_id, r);
      setResults(m);
      const ok = (data.results as PdfRenderResultRow[]).filter((r) => r.status !== "error").length;
      toast(`${ok} of ${data.results.length} ready`, "success");
      qc.invalidateQueries({ queryKey: ["pdf-roster", template.id] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const labelFor = (s: PdfStudentRosterRow) => {
    const r = results.get(s.id);
    if (r) return r.status;
    if (s.cached_pdf_id) return "cached";
    return "—";
  };

  const pdfIdFor = (s: PdfStudentRosterRow): number | null =>
    results.get(s.id)?.pdf_id ?? s.cached_pdf_id ?? null;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>Generate PDFs</span>
          <div className="flex items-center gap-3">
            <label className="flex items-center gap-1.5 text-sm font-normal">
              <Checkbox checked={force} onCheckedChange={(v) => setForce(!!v)} />
              Force re-render (ignore cache)
            </label>
            <Button onClick={() => render.mutate()} disabled={render.isPending || selected.size === 0}>
              <RefreshCw className="h-4 w-4" /> {render.isPending ? "Generating…" : `Generate ${selected.size || ""}`}
            </Button>
          </div>
        </CardTitle>
      </CardHeader>
      <CardContent className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12"><Checkbox checked={allChecked} onCheckedChange={toggleAll} /></TableHead>
              <TableHead>Student</TableHead>
              <TableHead>Data</TableHead>
              <TableHead>Status</TableHead>
              <TableHead className="text-right">Download</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {all.map((s) => {
              const r = results.get(s.id);
              const status = labelFor(s);
              const pdfId = pdfIdFor(s);
              return (
                <TableRow key={s.id}>
                  <TableCell><Checkbox checked={selected.has(s.id)} onCheckedChange={() => toggle(s.id)} /></TableCell>
                  <TableCell className="font-medium">{s.name}</TableCell>
                  <TableCell>
                    {s.has_data ? <Badge variant="success">filled</Badge> : <Badge variant="warning">missing</Badge>}
                  </TableCell>
                  <TableCell>
                    {status === "rendered" && <Badge variant="success">rendered</Badge>}
                    {status === "cached" && <Badge variant="info">cached</Badge>}
                    {status === "error" && <Badge variant="destructive" title={r?.error ?? ""}>error</Badge>}
                    {status === "—" && <span className="text-xs text-muted-foreground">—</span>}
                    {r?.error && <div className="text-xs text-red-700 mt-1 max-w-md">{r.error}</div>}
                  </TableCell>
                  <TableCell className="text-right">
                    {pdfId
                      ? <Button size="icon" variant="outline" onClick={() => downloadCachedPdf(pdfId, `${template.kind}-${s.name.replace(/\s+/g, "-")}`)}><FileDown className="h-4 w-4" /></Button>
                      : <span className="text-xs text-muted-foreground">—</span>}
                  </TableCell>
                </TableRow>
              );
            })}
            {!all.length && <TableRow><TableCell colSpan={5} className="text-center text-muted-foreground py-6">No students in this class</TableCell></TableRow>}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
