import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, Legend } from "chart.js";
import { FileSpreadsheet } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CLASSES } from "@/lib/utils";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { ATTENDANCE_TEMPLATE } from "@/lib/templates";
import type { Student, AttendanceRecord } from "@/types/api";
import { useTranslation } from "react-i18next";

ChartJS.register(ArcElement, Tooltip, Legend);

type Status = "P" | "A" | "L";

export default function Attendance() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);
  const [cls, setCls] = useState("");
  const [importOpen, setImportOpen] = useState(false);
  const [date, setDate] = useState(today);
  const [marks, setMarks] = useState<Record<number, Status>>({});

  const studentsQ = useQuery<Student[]>({
    queryKey: ["students", cls],
    queryFn: () => api.get("/students", { params: { class: cls, page_size: 500 } }).then((r) => r.data.items),
    enabled: !!cls,
  });

  const attQ = useQuery<AttendanceRecord | null>({
    queryKey: ["attendance", cls, date],
    queryFn: () => api.get("/attendance", { params: { class: cls, date } }).then((r) => r.data),
    enabled: !!cls && !!date,
  });

  const sortedStudents = useMemo(
    () => (studentsQ.data ?? []).slice().sort((a, b) => a.name.localeCompare(b.name)),
    [studentsQ.data]
  );

  // Initialize marks once students+att both load
  useMemo(() => {
    if (sortedStudents.length) {
      const m: Record<number, Status> = {};
      sortedStudents.forEach((s) => {
        m[s.id] = (attQ.data?.records?.[s.id] as Status) ?? "P";
      });
      setMarks(m);
    }
  }, [sortedStudents, attQ.data]);

  const save = useMutation({
    mutationFn: () => api.put("/attendance", { class_name: cls, date, records: marks }),
    onSuccess: () => {
      toast("Attendance saved", "success");
      qc.invalidateQueries({ queryKey: ["attendance", cls, date] });
      qc.invalidateQueries({ queryKey: ["attendance", "today"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const set = (id: number, st: Status) => setMarks((m) => ({ ...m, [id]: st }));
  const markAll = (st: Status) => {
    const next: Record<number, Status> = {};
    sortedStudents.forEach((s) => (next[s.id] = st));
    setMarks(next);
  };

  const counts = Object.values(marks).reduce(
    (acc, v) => ({ ...acc, [v]: (acc as Record<string, number>)[v] + 1 }),
    { P: 0, A: 0, L: 0 } as Record<Status, number>
  );

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.attendance")}</h1>
        <Button variant="outline" onClick={() => setImportOpen(true)}>
          <FileSpreadsheet className="h-4 w-4" /> Bulk import
        </Button>
      </div>

      <BulkImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bulk import attendance"
        description="One row per (class, date, student). Status must be P (Present), A (Absent), or L (Leave). Date accepted as YYYY-MM-DD, DD-MM-YYYY, or DD/MM/YYYY. Existing entries for the same (class, date) are replaced."
        templateCsv={ATTENDANCE_TEMPLATE}
        templateFilename="attendance-template.csv"
        uploadPath="/attendance/bulk-import"
        onSuccess={() => {
          qc.invalidateQueries({ queryKey: ["attendance"] });
          qc.invalidateQueries({ queryKey: ["attendance", "today"] });
        }}
      />

      <Card>
        <CardContent className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 mt-1">
          <div className="space-y-1.5">
            <Label>Class</Label>
            <Select value={cls} onValueChange={setCls}>
              <SelectTrigger><SelectValue placeholder="Select class" /></SelectTrigger>
              <SelectContent>{allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Date</Label><DatePicker value={date} onChange={setDate} /></div>
          <div className="flex items-end gap-2">
            <Button onClick={() => markAll("P")} variant="outline">All P</Button>
            <Button onClick={() => markAll("A")} variant="outline">All A</Button>
            <Button onClick={() => save.mutate()} disabled={!cls || !sortedStudents.length || save.isPending} className="ml-auto">
              {save.isPending ? "Saving…" : "Save attendance"}
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>{cls ? `${cls} — ${date}` : "Select class & date"}</CardTitle></CardHeader>
          <CardContent>
            {!cls ? (
              <p className="text-muted-foreground text-sm">Pick a class to start</p>
            ) : !sortedStudents.length ? (
              <p className="text-muted-foreground text-sm">No students in this class</p>
            ) : (
              <div className="divide-y">
                {sortedStudents.map((s) => (
                  <div key={s.id} className="flex items-center justify-between py-2">
                    <span className="text-sm font-medium">{s.name}</span>
                    <div className="flex gap-1">
                      {(["P", "A", "L"] as Status[]).map((st) => (
                        <Button
                          key={st}
                          size="sm"
                          variant={marks[s.id] === st ? (st === "P" ? "success" : st === "A" ? "destructive" : "warning") : "outline"}
                          onClick={() => set(s.id, st)}
                        >{st}</Button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Summary</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-2 text-center mb-3">
              <Stat label="Present" value={counts.P} color="text-emerald-600" />
              <Stat label="Absent" value={counts.A} color="text-red-600" />
              <Stat label="Leave" value={counts.L} color="text-amber-600" />
            </div>
            {Object.values(marks).length > 0 && (
              <Doughnut
                data={{
                  labels: ["Present", "Absent", "Leave"],
                  datasets: [{ data: [counts.P, counts.A, counts.L], backgroundColor: ["#22c55e", "#ef4444", "#f59e0b"], borderWidth: 0 }],
                }}
                options={{ plugins: { legend: { position: "bottom" } } }}
              />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Stat({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div>
      <div className={`text-2xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-muted-foreground">{label}</div>
    </div>
  );
}
