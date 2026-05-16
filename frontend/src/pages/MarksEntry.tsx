import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { FileSpreadsheet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CLASSES } from "@/lib/utils";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { MARKS_TEMPLATE } from "@/lib/templates";
import type { Student } from "@/types/api";
import { useTranslation } from "react-i18next";

const EXAMS = ["Unit Test 1", "Unit Test 2", "Half Yearly", "Pre-Board", "Final / Annual"];

export default function MarksEntry() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;
  const [cls, setCls] = useState("");
  const [exam, setExam] = useState(EXAMS[0]);
  const [subject, setSubject] = useState("");
  const [maxMarks, setMaxMarks] = useState(100);
  const [session, setSession] = useState(`${new Date().getFullYear()}-${String((new Date().getFullYear() + 1) % 100).padStart(2, "0")}`);
  const [marks, setMarks] = useState<Record<number, string>>({});
  const [importOpen, setImportOpen] = useState(false);
  const qc = useQueryClient();

  const studentsQ = useQuery<Student[]>({
    queryKey: ["students", cls],
    queryFn: () => api.get("/students", { params: { class: cls, page_size: 500 } }).then((r) => r.data.items),
    enabled: !!cls,
  });

  const save = useMutation({
    mutationFn: () =>
      api.post("/marks/bulk", {
        class_name: cls, exam_type: exam, subject, max_marks: maxMarks, session,
        items: Object.entries(marks).filter(([, v]) => v !== "").map(([id, v]) => ({ student_id: Number(id), marks: Number(v) })),
      }),
    onSuccess: (r: any) => { toast(`Saved marks for ${r.data.saved} students`, "success"); setMarks({}); },
    onError: (e) => toast(apiError(e), "error"),
  });

  const sorted = (studentsQ.data ?? []).slice().sort((a, b) => a.name.localeCompare(b.name));

  return (
    <div className="space-y-4 max-w-3xl">
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
        description="One row per (student × subject). Required: class_name, exam_type, subject, student_id, marks. Defaults: max_marks=100, session=blank. Each row creates a new marks entry — re-running will duplicate, so prefer importing fresh exam batches."
        templateCsv={MARKS_TEMPLATE}
        templateFilename="marks-template.csv"
        uploadPath="/marks/bulk-import"
        onSuccess={() => qc.invalidateQueries({ queryKey: ["marks"] })}
      />
      <Card>
        <CardHeader><CardTitle>Exam details</CardTitle></CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3">
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
          <div className="space-y-1.5"><Label>Subject</Label>
            <Input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="e.g. Mathematics" />
          </div>
          <div className="space-y-1.5"><Label>Max marks</Label>
            <Input type="number" value={maxMarks} onChange={(e) => setMaxMarks(Number(e.target.value) || 100)} />
          </div>
          <div className="space-y-1.5"><Label>Session</Label>
            <Input value={session} onChange={(e) => setSession(e.target.value)} placeholder="2025-26" />
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader><CardTitle>Enter marks</CardTitle></CardHeader>
        <CardContent>
          {!cls ? (
            <p className="text-muted-foreground text-sm">Select a class to load students.</p>
          ) : !sorted.length ? (
            <p className="text-muted-foreground text-sm">No students in this class.</p>
          ) : (
            <>
              <div className="space-y-2 mb-4">
                {sorted.map((s) => (
                  <div key={s.id} className="flex items-center gap-3">
                    <span className="flex-1 text-sm font-medium">{s.name}</span>
                    <Input
                      type="number"
                      className="w-24"
                      placeholder="—"
                      value={marks[s.id] ?? ""}
                      onChange={(e) => setMarks({ ...marks, [s.id]: e.target.value })}
                    />
                  </div>
                ))}
              </div>
              <Button onClick={() => save.mutate()} disabled={!subject || save.isPending}>
                {save.isPending ? "Saving…" : "Save marks"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
