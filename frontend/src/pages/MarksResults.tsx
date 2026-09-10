import { useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Printer, FileStack } from "lucide-react";
import { api } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CLASSES } from "@/lib/utils";
import type { ClassResults, ResultScope } from "@/types/api";
import { useTranslation } from "react-i18next";

const defaultSession = () => {
  const y = new Date().getFullYear();
  return `${y}-${String((y + 1) % 100).padStart(2, "0")}`;
};

const SCOPES: { value: ResultScope; label: string }[] = [
  { value: "annual", label: "Annual (full year)" },
  { value: "term1", label: "Term 1" },
  { value: "term2", label: "Term 2" },
];

const fmtMark = (n: number) => (Number.isInteger(n) ? String(n) : n.toFixed(1));

export default function MarksResults() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;
  const [cls, setCls] = useState("");
  const [session, setSession] = useState(defaultSession);
  const [scope, setScope] = useState<ResultScope>("annual");

  const resultsQ = useQuery<ClassResults>({
    queryKey: ["results", cls, session, scope],
    queryFn: () =>
      api.get("/marks/results", { params: { class: cls, session, scope } }).then((r) => r.data),
    enabled: !!cls && !!session,
  });

  const data = resultsQ.data;
  const columns = data?.subject_columns ?? [];
  // Show only students who actually have at least one mark in this scope.
  const rows = (data?.students ?? []).filter((s) =>
    s.subjects.some((sub) => sub.status !== "missing"),
  );
  const scopeLabel = SCOPES.find((s) => s.value === scope)?.label ?? scope;

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
        <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4">
          <div className="space-y-1.5"><Label>Class</Label>
            <Select value={cls} onValueChange={setCls}>
              <SelectTrigger><SelectValue placeholder="Select" /></SelectTrigger>
              <SelectContent>{allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5"><Label>Session</Label>
            <Input value={session} onChange={(e) => setSession(e.target.value)} placeholder="2025-26" />
          </div>
          <div className="space-y-1.5"><Label>Scope</Label>
            <Select value={scope} onValueChange={(v) => setScope(v as ResultScope)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>{SCOPES.map((s) => <SelectItem key={s.value} value={s.value}>{s.label}</SelectItem>)}</SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>{cls ? `${cls} — ${scopeLabel} · ${session}` : "Select class, session and scope"}</CardTitle>
        </CardHeader>
        <CardContent>
          {!cls ? (
            <p className="text-muted-foreground text-sm">Select a class to view results.</p>
          ) : resultsQ.isLoading ? (
            <p className="text-muted-foreground text-sm">Loading…</p>
          ) : !columns.length ? (
            <p className="text-muted-foreground text-sm">
              No subjects configured for this class. Set them up under Class Subjects first.
            </p>
          ) : !rows.length ? (
            <p className="text-muted-foreground text-sm">No marks entered for this class, session and scope yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>#</TableHead>
                    <TableHead>Student</TableHead>
                    {columns.map((c) => (
                      <TableHead key={c.subject_name} className="whitespace-nowrap text-center">
                        {c.subject_name}
                        {c.max > 0 && <span className="block text-[10px] font-normal text-muted-foreground">/{fmtMark(c.max)}</span>}
                      </TableHead>
                    ))}
                    <TableHead className="text-center">Total</TableHead>
                    <TableHead className="text-center">%</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {rows.map((r, i) => (
                    <TableRow key={r.student_id}>
                      <TableCell>{i + 1}</TableCell>
                      <TableCell className="font-medium whitespace-nowrap">
                        {r.roll_no ? <span className="text-muted-foreground mr-1">{r.roll_no}</span> : null}
                        {r.name}
                      </TableCell>
                      {columns.map((c) => {
                        const sub = r.subjects.find((s) => s.subject_name === c.subject_name);
                        if (!sub || c.max === 0) {
                          // Grading subjects (no numeric marks) — graded on the report card.
                          return <TableCell key={c.subject_name} className="text-center text-muted-foreground">—</TableCell>;
                        }
                        const dot =
                          sub.status === "partial" ? "bg-amber-500"
                          : sub.status === "missing" ? "bg-muted-foreground/40"
                          : "";
                        return (
                          <TableCell key={c.subject_name} className="text-center whitespace-nowrap">
                            {sub.status === "missing" ? (
                              <span className="text-muted-foreground">—</span>
                            ) : (
                              <span className="inline-flex items-center gap-1">
                                {dot && <span className={`inline-block h-1.5 w-1.5 rounded-full ${dot}`} title={sub.status} />}
                                {fmtMark(sub.obtained)}
                              </span>
                            )}
                          </TableCell>
                        );
                      })}
                      <TableCell className="text-center font-bold whitespace-nowrap">
                        {fmtMark(r.total_obtained)}<span className="text-muted-foreground font-normal">/{fmtMark(r.total_max)}</span>
                      </TableCell>
                      <TableCell className="text-center">
                        {r.percentage == null ? (
                          <span className="text-muted-foreground">—</span>
                        ) : (
                          <Badge variant={r.percentage >= 75 ? "success" : r.percentage >= 50 ? "warning" : "destructive"}>
                            {r.percentage}%
                          </Badge>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
