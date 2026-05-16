import { useState, useMemo } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, FileDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { CLASSES, formatCurrency } from "@/lib/utils";
import type { FeePayment, Student } from "@/types/api";
import { useTranslation } from "react-i18next";

const MONTHS = ["April", "May", "June", "July", "August", "September", "October", "November", "December", "January", "February", "March"];

export default function Fees() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const today = new Date().toISOString().slice(0, 10);

  const [filterClass, setFilterClass] = useState("");
  const [filterMonth, setFilterMonth] = useState("");

  const [cls, setCls] = useState("");
  const [studentId, setStudentId] = useState<string>("");
  const [month, setMonth] = useState(MONTHS[new Date().getMonth() < 3 ? new Date().getMonth() + 9 : new Date().getMonth() - 3]);
  const [year, setYear] = useState(`${new Date().getFullYear()}-${String((new Date().getFullYear() + 1) % 100).padStart(2, "0")}`);
  const [amount, setAmount] = useState("");
  const [date, setDate] = useState(today);
  const [receipt, setReceipt] = useState("");

  const studentsQ = useQuery<Student[]>({
    queryKey: ["students", cls],
    queryFn: () => api.get("/students", { params: { class: cls, page_size: 500 } }).then((r) => r.data.items),
    enabled: !!cls,
  });

  const feesQ = useQuery<FeePayment[]>({
    queryKey: ["fees", filterClass || "all", filterMonth || "all"],
    queryFn: () => api.get("/fees", { params: { ...(filterClass && { class: filterClass }), ...(filterMonth && { month: filterMonth }) } }).then((r) => r.data),
  });
  useSSE("fees", [["fees"]]);

  const saveFee = useMutation({
    mutationFn: () => api.post("/fees", {
      student_id: Number(studentId), class_name: cls, month, year, amount: Number(amount), date, receipt_no: receipt || undefined,
    }),
    onSuccess: () => {
      toast(`Fee ${formatCurrency(Number(amount))} recorded`, "success");
      setAmount(""); setReceipt("");
      qc.invalidateQueries({ queryKey: ["fees"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const deleteFee = useMutation({
    mutationFn: (id: number) => api.delete(`/fees/${id}`),
    onSuccess: () => { toast("Fee deleted", "warning"); qc.invalidateQueries({ queryKey: ["fees"] }); },
    onError: (e) => toast(apiError(e), "error"),
  });

  const total = useMemo(() => (feesQ.data ?? []).reduce((s, r) => s + Number(r.amount), 0), [feesQ.data]);

  const selectedStudent = useMemo(
    () => (studentsQ.data ?? []).find((s) => String(s.id) === studentId) ?? null,
    [studentsQ.data, studentId]
  );

  return (
    <div className="space-y-4">
      <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.fees")}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <Card>
          <CardHeader><CardTitle>Record fee payment</CardTitle></CardHeader>
          <CardContent>
            <form className="space-y-3" onSubmit={(e) => { e.preventDefault(); if (!studentId || !amount) return toast("Pick a student & amount", "warning"); saveFee.mutate(); }}>
              <div className="grid grid-cols-2 gap-2">
                <div className="space-y-1.5"><Label>Class</Label>
                  <Select value={cls} onValueChange={(v) => { setCls(v); setStudentId(""); }}>
                    <SelectTrigger><SelectValue placeholder="Class" /></SelectTrigger>
                    <SelectContent>{CLASSES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Student</Label>
                  <Select value={studentId} onValueChange={setStudentId} disabled={!cls}>
                    <SelectTrigger><SelectValue placeholder="Student" /></SelectTrigger>
                    <SelectContent>
                      {(studentsQ.data ?? []).map((s) => {
                        const tail = [
                          s.roll_no && `Roll ${s.roll_no}`,
                          s.admission_id,
                          s.father,
                        ].filter(Boolean).join(" · ");
                        return (
                          <SelectItem key={s.id} value={String(s.id)}>
                            {s.name}{tail && ` — ${tail}`}
                          </SelectItem>
                        );
                      })}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Month</Label>
                  <Select value={month} onValueChange={setMonth}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>{MONTHS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div className="space-y-1.5"><Label>Year</Label><Input value={year} onChange={(e) => setYear(e.target.value)} /></div>
                <div className="space-y-1.5"><Label>Amount (₹)</Label><Input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} required /></div>
                <div className="space-y-1.5"><Label>Date</Label><DatePicker value={date} onChange={setDate} /></div>
                <div className="space-y-1.5 col-span-2"><Label>Receipt (auto if blank)</Label><Input value={receipt} onChange={(e) => setReceipt(e.target.value)} /></div>
              </div>

              {selectedStudent && (
                <div className="rounded-md border border-khalsa-blue/20 bg-khalsa-blue/5 px-3 py-2.5 text-sm">
                  <div className="text-xs uppercase tracking-wide text-muted-foreground mb-1.5">Confirm student</div>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    <DetailRow label="Name" value={<b>{selectedStudent.name}</b>} />
                    <DetailRow label="Class" value={<b>{selectedStudent.class_name}</b>} />
                    <DetailRow label="Adm. ID" value={selectedStudent.admission_id ? <code className="font-mono text-xs">{selectedStudent.admission_id}</code> : "—"} />
                    <DetailRow label="Roll" value={selectedStudent.roll_no ? <b>{selectedStudent.roll_no}</b> : "—"} />
                    <DetailRow label="Father" value={selectedStudent.father || "—"} />
                    <DetailRow label="Mother" value={selectedStudent.mother || "—"} />
                    <DetailRow label="DOB" value={selectedStudent.dob ?? "—"} />
                    <DetailRow label="Phone" value={selectedStudent.phone || "—"} />
                    {selectedStudent.village && <DetailRow label="Village" value={selectedStudent.village} />}
                    {Number(selectedStudent.annual_fee) > 0 && (
                      <DetailRow label="Annual fee" value={formatCurrency(Number(selectedStudent.annual_fee))} />
                    )}
                  </div>
                </div>
              )}

              <Button type="submit" disabled={saveFee.isPending}>{saveFee.isPending ? "Saving…" : "Record payment"}</Button>
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle className="flex items-center justify-between">
            <span>Fee records</span>
            <span className="text-emerald-600 text-sm font-bold">Total {formatCurrency(total)}</span>
          </CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-2 mb-3">
              <div className="space-y-1.5"><Label>Filter by class</Label>
                <Select value={filterClass || "__all"} onValueChange={(v) => setFilterClass(v === "__all" ? "" : v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all">All classes</SelectItem>
                    {CLASSES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5"><Label>Filter by month</Label>
                <Select value={filterMonth || "__all"} onValueChange={(v) => setFilterMonth(v === "__all" ? "" : v)}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="__all">All months</SelectItem>
                    {MONTHS.map((m) => <SelectItem key={m} value={m}>{m}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <Table>
              <TableHeader>
                <TableRow><TableHead>Receipt</TableHead><TableHead>Student</TableHead><TableHead>Class</TableHead><TableHead>Month</TableHead><TableHead>Amount</TableHead><TableHead></TableHead></TableRow>
              </TableHeader>
              <TableBody>
                {(feesQ.data ?? []).map((r) => (
                  <TableRow key={r.id}>
                    <TableCell><code className="text-xs">{r.receipt_no}</code></TableCell>
                    <TableCell className="font-medium">{r.student_name}</TableCell>
                    <TableCell><Badge variant="info">{r.class_name}</Badge></TableCell>
                    <TableCell>{r.month} {r.year}</TableCell>
                    <TableCell className="text-emerald-600 font-bold">{formatCurrency(Number(r.amount))}</TableCell>
                    <TableCell className="flex gap-1">
                      <Button
                        size="icon"
                        variant="outline"
                        title={t("portal.common.download") + " · PDF"}
                        onClick={async () => {
                          try {
                            const stu = await api
                              .get<Student>(`/students/${r.student_id}`)
                              .then((x) => x.data)
                              .catch(() => null);
                            const payload = {
                              receiptNo: r.receipt_no,
                              date: r.date,
                              term: `${r.month} ${r.year}`,
                              student: {
                                name: stu?.name || r.student_name,
                                class: r.class_name,
                                rollNo: stu?.roll_no || String(r.student_id),
                                admissionNo: stu?.admission_id ?? null,
                                fatherName: stu?.father || null,
                              },
                              items: [
                                {
                                  particulars: `Fee — ${r.month} ${r.year}`,
                                  amount: Number(r.amount),
                                },
                              ],
                              total: Number(r.amount),
                              modeOfPayment: "Cash" as const,
                            };
                            const res = await api.post(`/pdf/fee-receipt`, payload, { responseType: "blob" });
                            const url = URL.createObjectURL(res.data as Blob);
                            const a = document.createElement("a");
                            a.href = url;
                            a.download = `${r.receipt_no || "receipt"}.pdf`;
                            a.click();
                            URL.revokeObjectURL(url);
                          } catch (e) {
                            toast(apiError(e), "error");
                          }
                        }}
                      >
                        <FileDown className="h-4 w-4" />
                      </Button>
                      <Button size="icon" variant="outline" className="text-destructive" onClick={() => confirm("Delete fee?") && deleteFee.mutate(r.id)}>
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </TableCell>
                  </TableRow>
                ))}
                {!feesQ.data?.length && <TableRow><TableCell colSpan={6} className="text-center text-muted-foreground py-6">No fee records</TableCell></TableRow>}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function DetailRow({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline gap-2 min-w-0">
      <span className="text-muted-foreground text-xs shrink-0 w-20">{label}</span>
      <span className="truncate">{value}</span>
    </div>
  );
}
