import { useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Printer, FileStack } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CLASSES } from "@/lib/utils";
import type { Mark, Student } from "@/types/api";
import { useTranslation } from "react-i18next";

const EXAMS = ["Unit Test 1", "Unit Test 2", "Half Yearly", "Pre-Board", "Final / Annual"];

export default function MarksResults() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;
  const [cls, setCls] = useState("");
  const [exam, setExam] = useState(EXAMS[0]);

  const marksQ = useQuery<Mark[]>({
    queryKey: ["marks", cls, exam],
    queryFn: () => api.get("/marks", { params: { class: cls, exam_type: exam } }).then((r) => r.data),
    enabled: !!cls && !!exam,
  });
  const studentsQ = useQuery<Student[]>({
    queryKey: ["students", cls],
    queryFn: () => api.get("/students", { params: { class: cls, page_size: 500 } }).then((r) => r.data.items),
    enabled: !!cls,
  });

  const { rows, subjects } = useMemo(() => {
    const subj = new Set<string>();
    const map = new Map<number, { id: number; name: string; marks: Record<string, number> }>();
    (studentsQ.data ?? []).forEach((s) => map.set(s.id, { id: s.id, name: s.name, marks: {} }));
    (marksQ.data ?? []).forEach((m) => {
      subj.add(m.subject);
      const e = map.get(m.student_id);
      if (e) e.marks[m.subject] = m.marks;
    });
    const subjects = [...subj].sort();
    const rows = [...map.values()].filter((v) => Object.keys(v.marks).length);
    return { rows, subjects };
  }, [marksQ.data, studentsQ.data]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.marksResults")}</h1>
        <Button variant="outline" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print</Button>
      </div>

      <div className="rounded-md border border-border bg-cream/40 p-3 text-sm flex items-center gap-3">
        <FileStack className="h-5 w-5 text-khalsa-blue shrink-0" />
        <span>
          Need report cards? They're now generated from a saved class template so you only fill the common fields once.
          Open <Link to="/templates" className="underline font-semibold">Templates</Link> to create one for this class and term.
        </span>
      </div>

      <Card>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3 p-4">
          <div className="space-y-1.5"><Label>Class</Label>
            <Select value={cls} onValueChange={setCls}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Exam type</Label>
            <Select value={exam} onValueChange={setExam}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{EXAMS.map((e) => <SelectItem key={e} value={e}>{e}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>{cls ? `${cls} — ${exam}` : "Select class and exam"}</CardTitle></CardHeader>
        <CardContent>
          {!rows.length ? (
            <p className="text-muted-foreground text-sm">No results to show.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>#</TableHead><TableHead>Student</TableHead>
                  {subjects.map((s) => <TableHead key={s}>{s}</TableHead>)}
                  <TableHead>Total</TableHead><TableHead>%</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {rows.map((r, i) => {
                  const tot = subjects.reduce((s, sub) => s + (r.marks[sub] ?? 0), 0);
                  const pct = subjects.length ? Math.round((tot / (subjects.length * 100)) * 100) : 0;
                  return (
                    <TableRow key={i}>
                      <TableCell>{i + 1}</TableCell>
                      <TableCell className="font-medium">{r.name}</TableCell>
                      {subjects.map((s) => <TableCell key={s}>{r.marks[s] ?? "—"}</TableCell>)}
                      <TableCell className="font-bold">{tot}</TableCell>
                      <TableCell>
                        <Badge variant={pct >= 75 ? "success" : pct >= 50 ? "warning" : "destructive"}>{pct}%</Badge>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
