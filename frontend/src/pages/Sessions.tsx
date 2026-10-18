import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { CalendarRange, Pencil, Plus } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { DatePicker } from "@/components/ui/date-picker";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { defaultSessionName, useSessions } from "@/lib/session";
import { formatDate } from "@/lib/utils";
import type { AcademicSession } from "@/types/api";

type DateKey = "starts_on" | "ends_on" | "term1_start" | "term1_end" | "term2_start" | "term2_end";
type Form = Record<DateKey, string> & { session: string; is_current: boolean };

/** Default calendar for a session name: Apr 1 - Mar 31, Term 1 Apr-Sep, Term 2 Oct-Mar. */
function defaultsFor(name: string): Form {
  const y = Number(name.slice(0, 4)) || new Date().getFullYear();
  return {
    session: name,
    starts_on: `${y}-04-01`, ends_on: `${y + 1}-03-31`,
    term1_start: `${y}-04-01`, term1_end: `${y}-09-30`,
    term2_start: `${y}-10-01`, term2_end: `${y + 1}-03-31`,
    is_current: false,
  };
}

function nextSessionName(rows: AcademicSession[]): string {
  const latest = rows.map((r) => Number(r.session.slice(0, 4))).filter(Boolean).sort((a, b) => b - a)[0];
  if (!latest) return defaultSessionName();
  const y = latest + 1;
  return `${y}-${String((y + 1) % 100).padStart(2, "0")}`;
}

const range = (a: string, b: string) => `${formatDate(a)} – ${formatDate(b)}`;

export default function Sessions() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { data: rows = [], isLoading } = useSessions();
  const [editing, setEditing] = useState<AcademicSession | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Form>(defaultsFor(defaultSessionName()));

  const save = useMutation({
    mutationFn: () => {
      const { session, ...rest } = form;
      return editing ? api.patch(`/sessions/${editing.id}`, rest) : api.post("/sessions", { session, ...rest });
    },
    onSuccess: () => {
      toast(t("portal.sessions.saved"), "success");
      setEditing(null);
      setCreating(false);
      qc.invalidateQueries({ queryKey: ["sessions"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const openCreate = () => {
    setForm(defaultsFor(nextSessionName(rows)));
    setEditing(null);
    setCreating(true);
  };
  const openEdit = (row: AcademicSession) => {
    setForm({
      session: row.session, is_current: row.is_current,
      starts_on: row.starts_on, ends_on: row.ends_on,
      term1_start: row.term1_start, term1_end: row.term1_end,
      term2_start: row.term2_start, term2_end: row.term2_end,
    });
    setCreating(false);
    setEditing(row);
  };
  const setDate = (k: DateKey) => (iso: string) => setForm((f) => ({ ...f, [k]: iso }));
  const dialogOpen = creating || !!editing;

  return (
    <div className="space-y-4 max-w-5xl">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="font-display text-heading-lg text-deep-indigo flex items-center gap-2">
            <CalendarRange className="h-6 w-6" /> {t("portal.sessions.title")}
          </h1>
          <p className="text-sm text-muted-foreground mt-1">{t("portal.sessions.subtitle")}</p>
        </div>
        <Button onClick={openCreate}><Plus className="h-4 w-4" /> {t("portal.sessions.add")}</Button>
      </div>

      <Card>
        <CardContent className="p-0 overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("portal.sessions.session")}</TableHead>
                <TableHead>{t("portal.sessions.dates")}</TableHead>
                <TableHead>{t("portal.sessions.term1")}</TableHead>
                <TableHead>{t("portal.sessions.term2")}</TableHead>
                <TableHead />
              </TableRow>
            </TableHeader>
            <TableBody>
              {isLoading ? (
                <TableRow><TableCell colSpan={5} className="text-muted-foreground">Loading…</TableCell></TableRow>
              ) : rows.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-semibold whitespace-nowrap">
                    {r.session}{" "}
                    {r.is_current && <Badge variant="success" className="ml-1">{t("portal.sessions.current")}</Badge>}
                  </TableCell>
                  <TableCell className="whitespace-nowrap">{range(r.starts_on, r.ends_on)}</TableCell>
                  <TableCell className="whitespace-nowrap">{range(r.term1_start, r.term1_end)}</TableCell>
                  <TableCell className="whitespace-nowrap">{range(r.term2_start, r.term2_end)}</TableCell>
                  <TableCell className="text-right">
                    <Button variant="ghost" size="sm" onClick={() => openEdit(r)} aria-label={t("portal.sessions.edit")}>
                      <Pencil className="h-4 w-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onOpenChange={(o) => { if (!o) { setCreating(false); setEditing(null); } }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editing ? `${t("portal.sessions.edit")} · ${editing.session}` : t("portal.sessions.add")}</DialogTitle>
            <DialogDescription>{t("portal.sessions.dialogHint")}</DialogDescription>
          </DialogHeader>
          <div className="grid grid-cols-2 gap-3">
            {creating && (
              <div className="col-span-2 space-y-1.5">
                <Label>{t("portal.sessions.session")}</Label>
                <Input
                  value={form.session}
                  placeholder="2027-28"
                  onChange={(e) => {
                    const v = e.target.value.trim();
                    setForm((f) => (/^\d{4}-\d{2}$/.test(v) ? { ...defaultsFor(v), is_current: f.is_current } : { ...f, session: v }));
                  }}
                />
              </div>
            )}
            {([
              ["starts_on", "portal.sessions.starts"], ["ends_on", "portal.sessions.ends"],
              ["term1_start", "portal.sessions.term1Start"], ["term1_end", "portal.sessions.term1End"],
              ["term2_start", "portal.sessions.term2Start"], ["term2_end", "portal.sessions.term2End"],
            ] as [DateKey, string][]).map(([k, label]) => (
              <div key={k} className="space-y-1.5">
                <Label>{t(label)}</Label>
                <DatePicker value={form[k]} onChange={setDate(k)} />
              </div>
            ))}
            <label className="col-span-2 flex items-center gap-2 text-sm">
              <Checkbox
                checked={form.is_current}
                onCheckedChange={(v) => setForm((f) => ({ ...f, is_current: v === true }))}
              />
              {t("portal.sessions.makeCurrent")}
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => { setCreating(false); setEditing(null); }}>Cancel</Button>
            <Button onClick={() => save.mutate()} disabled={save.isPending}>
              {save.isPending ? "Saving…" : t("portal.actions.saveChanges")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
