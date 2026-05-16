import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Printer, Users, Wallet, ClipboardCheck, Briefcase } from "lucide-react";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { api } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { useTranslation } from "react-i18next";

type ReportKey = "class-wise" | "fee-summary" | "attendance-monthly" | "staff-list";

export default function Reports() {
  const { t } = useTranslation();
  const [key, setKey] = useState<ReportKey | null>(null);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.reports")}</h1>
        {key && <Button variant="outline" onClick={() => window.print()}><Printer className="h-4 w-4" /> Print</Button>}
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        <ReportCard title="Class-wise students" icon={<Users />} active={key === "class-wise"} onClick={() => setKey("class-wise")} />
        <ReportCard title="Fee collection" icon={<Wallet />} active={key === "fee-summary"} onClick={() => setKey("fee-summary")} />
        <ReportCard title="Attendance" icon={<ClipboardCheck />} active={key === "attendance-monthly"} onClick={() => setKey("attendance-monthly")} />
        <ReportCard title="Staff directory" icon={<Briefcase />} active={key === "staff-list"} onClick={() => setKey("staff-list")} />
      </div>

      {key === "class-wise" && <ClassWise />}
      {key === "fee-summary" && <FeeSummary />}
      {key === "attendance-monthly" && <AttendanceMonthly />}
      {key === "staff-list" && <StaffList />}
    </div>
  );
}

function ReportCard({ title, icon, active, onClick }: { title: string; icon: React.ReactNode; active: boolean; onClick: () => void }) {
  return (
    <Card onClick={onClick} className={`cursor-pointer hover:shadow-md transition-shadow ${active ? "ring-2 ring-primary" : ""}`}>
      <CardContent className="p-5 flex items-center gap-3">
        <div className="bg-primary/10 text-primary p-2 rounded">{icon}</div>
        <div className="font-medium">{title}</div>
      </CardContent>
    </Card>
  );
}

interface ClassRow { class: string; count: number; students: { id: number; name: string; father: string; dob: string; phone: string }[] }
function ClassWise() {
  const { data = [] } = useQuery<ClassRow[]>({ queryKey: ["report", "class-wise"], queryFn: () => api.get("/reports/class-wise").then((r) => r.data) });
  return (
    <Card>
      <CardHeader><CardTitle>Class-wise students — {new Date().toLocaleDateString("en-IN")}</CardTitle></CardHeader>
      <CardContent className="space-y-4">
        {data.map((g) => (
          <div key={g.class}>
            <h3 className="bg-primary text-primary-foreground px-3 py-1 rounded text-sm font-bold mb-2">{g.class} — {g.count} Students</h3>
            <Table>
              <TableHeader><TableRow><TableHead>#</TableHead><TableHead>Name</TableHead><TableHead>Father</TableHead><TableHead>DOB</TableHead><TableHead>Phone</TableHead></TableRow></TableHeader>
              <TableBody>
                {g.students.map((s, i) => (
                  <TableRow key={s.id}><TableCell>{i + 1}</TableCell><TableCell>{s.name}</TableCell><TableCell>{s.father}</TableCell><TableCell>{s.dob}</TableCell><TableCell>{s.phone}</TableCell></TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

interface FeeSummaryRow { rows: { month: string; total: number; count: number }[]; grand_total: number }
function FeeSummary() {
  const { data } = useQuery<FeeSummaryRow>({ queryKey: ["report", "fee-summary"], queryFn: () => api.get("/reports/fee-summary").then((r) => r.data) });
  if (!data) return null;
  return (
    <Card>
      <CardHeader><CardTitle>Fee collection — {new Date().toLocaleDateString("en-IN")}</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader><TableRow><TableHead>Month</TableHead><TableHead>Transactions</TableHead><TableHead>Total collected</TableHead></TableRow></TableHeader>
          <TableBody>
            {data.rows.map((r) => (
              <TableRow key={r.month}><TableCell>{r.month}</TableCell><TableCell>{r.count}</TableCell><TableCell className="text-emerald-600 font-bold">{formatCurrency(r.total)}</TableCell></TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="text-right mt-3 font-bold">Grand Total: {formatCurrency(data.grand_total)}</div>
      </CardContent>
    </Card>
  );
}

interface AttRow { class: string; date: string; present: number; absent: number; leave: number }
function AttendanceMonthly() {
  const { data = [] } = useQuery<AttRow[]>({ queryKey: ["report", "attendance-monthly"], queryFn: () => api.get("/reports/attendance-monthly").then((r) => r.data) });
  return (
    <Card>
      <CardHeader><CardTitle>Attendance report</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader><TableRow><TableHead>Date</TableHead><TableHead>Class</TableHead><TableHead>Present</TableHead><TableHead>Absent</TableHead><TableHead>Leave</TableHead><TableHead>Total</TableHead></TableRow></TableHeader>
          <TableBody>
            {data.map((r, i) => (
              <TableRow key={i}>
                <TableCell>{r.date}</TableCell><TableCell>{r.class}</TableCell>
                <TableCell className="text-emerald-600 font-bold">{r.present}</TableCell>
                <TableCell className="text-red-600">{r.absent}</TableCell>
                <TableCell className="text-amber-600">{r.leave}</TableCell>
                <TableCell>{r.present + r.absent + r.leave}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}

interface StaffRow { id: number; name: string; designation: string; assigned_classes: string[]; phone: string }
function StaffList() {
  const { data = [] } = useQuery<StaffRow[]>({ queryKey: ["report", "staff-list"], queryFn: () => api.get("/reports/staff-list").then((r) => r.data) });
  return (
    <Card>
      <CardHeader><CardTitle>Staff directory</CardTitle></CardHeader>
      <CardContent>
        <Table>
          <TableHeader><TableRow><TableHead>#</TableHead><TableHead>Name</TableHead><TableHead>Designation</TableHead><TableHead>Classes</TableHead><TableHead>Phone</TableHead></TableRow></TableHeader>
          <TableBody>
            {data.map((s, i) => (
              <TableRow key={s.id}>
                <TableCell>{i + 1}</TableCell><TableCell>{s.name}</TableCell>
                <TableCell>{s.designation}</TableCell><TableCell>{s.assigned_classes.join(", ")}</TableCell>
                <TableCell>{s.phone}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
