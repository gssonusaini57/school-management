import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import { FileDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { DatePicker } from "@/components/ui/date-picker";
import { toast } from "@/components/ui/toaster";
import { api } from "@/lib/api";
import { downloadPdf } from "@/lib/pdf";
import type { Staff } from "@/types/api";

const MONTHS = [
  ["01", "January"], ["02", "February"], ["03", "March"], ["04", "April"],
  ["05", "May"], ["06", "June"], ["07", "July"], ["08", "August"],
  ["09", "September"], ["10", "October"], ["11", "November"], ["12", "December"],
] as const;

type Earnings = { basic: string; hra: string; da: string; conveyance: string; special: string };
type Deductions = { pf: string; tds: string; profTax: string; advance: string; esi: string };

const num = (s: string) => Number(s) || 0;

export default function SalarySlips() {
  const { t } = useTranslation();

  const now = new Date();
  const [staffId, setStaffId] = useState<string>("");
  const [year, setYear] = useState(String(now.getFullYear()));
  const [month, setMonth] = useState(String(now.getMonth() + 1).padStart(2, "0"));

  const [earn, setEarn] = useState<Earnings>({ basic: "14000", hra: "1800", da: "3200", conveyance: "600", special: "700" });
  const [ded, setDed]   = useState<Deductions>({ pf: "280", tds: "0", profTax: "200", advance: "0", esi: "0" });

  const [workingDays, setWorkingDays] = useState("26");
  const [daysPresent, setDaysPresent] = useState("25");
  const [leaves, setLeaves] = useState("1");
  const [leaveType, setLeaveType] = useState("CL");

  const [pan, setPan] = useState("");
  const [contact, setContact] = useState("");
  const [doj, setDoj] = useState("");
  const [department, setDepartment] = useState("");
  const [bankAcc, setBankAcc] = useState("");
  const [bankIfsc, setBankIfsc] = useState("");
  const [bankName, setBankName] = useState("");
  const [busy, setBusy] = useState(false);

  const { data: staff = [] } = useQuery<Staff[]>({
    queryKey: ["staff"],
    queryFn: () => api.get("/staff").then((r) => r.data),
  });
  const selected = useMemo(() => staff.find((s) => String(s.id) === staffId), [staff, staffId]);

  const gross = num(earn.basic) + num(earn.hra) + num(earn.da) + num(earn.conveyance) + num(earn.special);
  const dedTotal = num(ded.pf) + num(ded.tds) + num(ded.profTax) + num(ded.advance) + num(ded.esi);
  const net = gross - dedTotal;

  const generate = async () => {
    if (!selected) return toast("Pick an employee first", "warning");
    if (net <= 0) return toast("Net pay must be greater than zero", "warning");

    const payload = {
      month: `${year}-${month}`,
      issuedDate: new Date().toISOString().slice(0, 10),
      employee: {
        id: `KIS-${selected.id}`,
        name: selected.name,
        designation: selected.designation || "Teacher",
        department: department || "—",
        doj: doj || null,
        pan: pan || null,
        contact: contact || selected.phone || null,
      },
      workingDays: num(workingDays) || null,
      daysPresent: num(daysPresent) || null,
      leavesTaken: num(leaves),
      leaveType: leaveType || null,
      earnings: {
        basic: num(earn.basic), hra: num(earn.hra), da: num(earn.da),
        conveyance: num(earn.conveyance), special: num(earn.special),
      },
      deductions: {
        pf: num(ded.pf), esi: num(ded.esi), tds: num(ded.tds),
        profTax: num(ded.profTax), advance: num(ded.advance),
      },
      netPay: net,
      bank: (bankAcc || bankIfsc || bankName) ? { accountNo: bankAcc, ifsc: bankIfsc, bankName } : null,
    };

    setBusy(true);
    try {
      const filename = `salary-slip-${selected.name.replace(/\s+/g, "-")}-${year}-${month}.pdf`;
      await downloadPdf("salary-slip", payload, filename);
      toast("Salary slip generated", "success");
    } catch {
      /* downloadPdf already toasted */
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-4">
      <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.salarySlips", "Salary Slips")}</h1>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Pay structure</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1.5 col-span-3">
                <Label>Employee *</Label>
                <Select value={staffId} onValueChange={setStaffId}>
                  <SelectTrigger><SelectValue placeholder="Select staff member" /></SelectTrigger>
                  <SelectContent>
                    {staff.map((s) => (
                      <SelectItem key={s.id} value={String(s.id)}>{s.name} — {s.designation}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5">
                <Label>Year</Label>
                <Input value={year} onChange={(e) => setYear(e.target.value)} maxLength={4} />
              </div>
              <div className="space-y-1.5 col-span-2">
                <Label>Month</Label>
                <Select value={month} onValueChange={setMonth}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {MONTHS.map(([v, l]) => <SelectItem key={v} value={v}>{l}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4 pt-2 border-t">
              <div className="space-y-2">
                <div className="text-sm font-semibold text-emerald-700">Earnings (₹)</div>
                {([
                  ["basic",      "Basic salary"],
                  ["da",         "Dearness allowance"],
                  ["hra",        "House rent allowance"],
                  ["conveyance", "Conveyance"],
                  ["special",    "Special allowance"],
                ] as const).map(([k, l]) => (
                  <div key={k} className="space-y-1">
                    <Label className="text-xs">{l}</Label>
                    <Input type="number" value={earn[k]} onChange={(e) => setEarn((s) => ({ ...s, [k]: e.target.value }))} />
                  </div>
                ))}
                <div className="text-xs text-muted-foreground pt-1">Gross: <b className="text-emerald-700">₹ {gross.toLocaleString("en-IN")}</b></div>
              </div>
              <div className="space-y-2">
                <div className="text-sm font-semibold text-red-700">Deductions (₹)</div>
                {([
                  ["pf",      "Provident fund"],
                  ["tds",     "TDS"],
                  ["profTax", "Professional tax"],
                  ["advance", "Loan / advance"],
                  ["esi",     "ESI"],
                ] as const).map(([k, l]) => (
                  <div key={k} className="space-y-1">
                    <Label className="text-xs">{l}</Label>
                    <Input type="number" value={ded[k]} onChange={(e) => setDed((s) => ({ ...s, [k]: e.target.value }))} />
                  </div>
                ))}
                <div className="text-xs text-muted-foreground pt-1">Total: <b className="text-red-700">₹ {dedTotal.toLocaleString("en-IN")}</b></div>
              </div>
            </div>

            <div className="rounded-lg bg-deep-indigo text-white p-4 flex items-center justify-between">
              <span className="text-sm tracking-widest font-semibold text-royal-gold">NET PAY</span>
              <span className="font-display font-bold text-3xl">₹ {net.toLocaleString("en-IN")}</span>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Attendance &amp; HR fields</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid grid-cols-3 gap-2">
              <div className="space-y-1.5"><Label>Working days</Label><Input type="number" value={workingDays} onChange={(e) => setWorkingDays(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Days present</Label><Input type="number" value={daysPresent} onChange={(e) => setDaysPresent(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Leaves</Label><Input type="number" value={leaves} onChange={(e) => setLeaves(e.target.value)} /></div>
            </div>
            <div className="space-y-1.5"><Label>Leave type</Label><Input value={leaveType} onChange={(e) => setLeaveType(e.target.value)} placeholder="CL / SL / EL" /></div>
            <div className="space-y-1.5"><Label>Department</Label><Input value={department} onChange={(e) => setDepartment(e.target.value)} placeholder="Pre-Primary &amp; Class I–V" /></div>
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5"><Label>PAN</Label><Input value={pan} onChange={(e) => setPan(e.target.value)} /></div>
              <div className="space-y-1.5"><Label>Contact</Label><Input value={contact} onChange={(e) => setContact(e.target.value)} /></div>
            </div>
            <div className="space-y-1.5"><Label>Date of joining</Label><DatePicker value={doj} onChange={setDoj} /></div>

            <div className="pt-2 border-t space-y-2">
              <div className="text-sm font-semibold">Bank (optional)</div>
              <Input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="Bank name" />
              <Input value={bankAcc} onChange={(e) => setBankAcc(e.target.value)} placeholder="Account no." />
              <Input value={bankIfsc} onChange={(e) => setBankIfsc(e.target.value)} placeholder="IFSC" />
            </div>

            <Button className="w-full mt-2" onClick={generate} disabled={busy}>
              <FileDown className="h-4 w-4" /> {busy ? "Generating…" : "Generate slip"}
            </Button>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
