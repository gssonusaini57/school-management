import { useEffect, useId, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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
import type { AcademicSession, SessionDefaults } from "@/types/api";

type DateKey = "starts_on" | "ends_on" | "term1_start" | "term1_end" | "term2_start" | "term2_end";
type Form = Record<DateKey, string> & { session: string; is_current: boolean };

const DATE_KEYS: DateKey[] = ["starts_on", "ends_on", "term1_start", "term1_end", "term2_start", "term2_end"];
const NO_DATES = Object.fromEntries(DATE_KEYS.map((k) => [k, ""])) as Record<DateKey, string>;
/** The shape of a session name; the server also checks that the years follow on (2027-28). */
const SESSION_NAME = /^\d{4}-\d{2}$/;

/** A new session's form. Its dates come from the server's default calendar (GET /sessions/defaults). */
function emptyForm(name: string): Form {
  return { session: name, ...NO_DATES, is_current: false };
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
  const uid = useId();
  const { data: rows = [], isLoading } = useSessions();
  const [editing, setEditing] = useState<AcademicSession | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState<Form>(emptyForm(defaultSessionName()));
  // The name whose default dates the create dialog shows: the typed one, after a pause.
  const [defaultsName, setDefaultsName] = useState("");
  useEffect(() => {
    if (!creating) return;
    const id = window.setTimeout(() => setDefaultsName(form.session), 300);
    return () => window.clearTimeout(id);
  }, [creating, form.session]);
  const defaultsQ = useQuery<SessionDefaults>({
    queryKey: ["session-defaults", defaultsName],
    queryFn: () => api.get("/sessions/defaults", { params: { session: defaultsName } }).then((r) => r.data),
    enabled: creating && SESSION_NAME.test(defaultsName),
    retry: false,
  });
  // Fill in the dates still empty once the server's defaults for the typed name arrive
  // (a date picked meanwhile is kept; another name clears them all, below).
  useEffect(() => {
    const d = defaultsQ.data;
    if (!creating || !d || form.session !== defaultsName) return;
    setForm((f) => {
      if (f.session !== defaultsName || DATE_KEYS.every((k) => f[k])) return f;
      const dates = Object.fromEntries(DATE_KEYS.map((k) => [k, f[k] || d[k] || ""])) as Record<DateKey, string>;
      return { ...f, ...dates };
    });
  }, [creating, defaultsQ.data, defaultsName, form.session]);
  const nameOk = SESSION_NAME.test(form.session);
  const missingDate = DATE_KEYS.some((k) => !form[k]);

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
      // Term dates decide which days count in the results' and the report cards' attendance.
      qc.invalidateQueries({ queryKey: ["results"] });
      qc.invalidateQueries({ queryKey: ["pdf-roster"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const openCreate = () => {
    const name = nextSessionName(rows);
    setForm(emptyForm(name));
    setDefaultsName(name);
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
                <TableRow><TableCell colSpan={5} className="text-muted-foreground">{t("portal.common.loading", "Loading…")}</TableCell></TableRow>
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
                    <Button variant="ghost" size="sm" onClick={() => openEdit(r)} aria-label={`${t("portal.sessions.edit")} · ${r.session}`}>
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
                <Label htmlFor={`${uid}-session`}>{t("portal.sessions.session")}</Label>
                <Input
                  id={`${uid}-session`}
                  value={form.session}
                  placeholder="2027-28"
                  onChange={(e) => {
                    const v = e.target.value.trim();
                    // Another name: its dates come from the server's defaults, not the last name's.
                    setForm((f) => (v === f.session ? f : { ...f, ...NO_DATES, session: v }));
                  }}
                />
                {!nameOk ? (
                  <p className="text-xs text-muted-foreground">
                    {t("portal.sessions.nameHint", "Write the session as two years, like 2027-28.")}
                  </p>
                ) : defaultsName === form.session && defaultsQ.isError ? (
                  <p className="text-xs text-destructive">
                    {t("portal.sessions.defaultsError", "Couldn't fill in the default dates, so pick them below.")}{" "}
                    {apiError(defaultsQ.error)}
                  </p>
                ) : missingDate && (defaultsQ.isFetching || defaultsName !== form.session) ? (
                  <p className="text-xs text-muted-foreground">
                    {t("portal.sessions.defaultsLoading", "Filling in the default dates…")}
                  </p>
                ) : null}
              </div>
            )}
            {([
              ["starts_on", "portal.sessions.starts"], ["ends_on", "portal.sessions.ends"],
              ["term1_start", "portal.sessions.term1Start"], ["term1_end", "portal.sessions.term1End"],
              ["term2_start", "portal.sessions.term2Start"], ["term2_end", "portal.sessions.term2End"],
            ] as [DateKey, string][]).map(([k, label]) => (
              <div key={k} className="space-y-1.5">
                <Label id={`${uid}-${k}-label`} htmlFor={`${uid}-${k}`}>{t(label)}</Label>
                <DatePicker id={`${uid}-${k}`} aria-labelledby={`${uid}-${k}-label`} value={form[k]} onChange={setDate(k)} />
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
            <Button variant="outline" onClick={() => { setCreating(false); setEditing(null); }}>{t("portal.common.cancel", "Cancel")}</Button>
            <Button onClick={() => save.mutate()} disabled={save.isPending || (creating && (!nameOk || missingDate))}>
              {save.isPending ? t("portal.common.saving", "Saving…") : t("portal.actions.saveChanges")}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
