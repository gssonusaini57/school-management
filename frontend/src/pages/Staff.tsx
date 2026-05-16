import { useEffect, useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2, FileSpreadsheet, Pencil, Copy, Check, Eye, EyeOff, Clock, Plus, AlertTriangle } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useSSE } from "@/lib/sse";
import { CLASSES } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { BulkImportDialog } from "@/components/BulkImportDialog";
import { STAFF_TEMPLATE } from "@/lib/templates";
import type { Staff, StaffCreateResponse, StaffUpdateResponse } from "@/types/api";
import { useTranslation } from "react-i18next";

const DESIGNATIONS = ["Class Teacher", "Subject Teacher", "Principal", "Vice Principal", "Librarian", "Office Staff", "Support Staff"];

const isPlaceholderEmail = (email: string) => /@kis\.local$/i.test(email);

// Legacy staff rows have inconsistent class-name spellings (e.g. "LKG" vs "L.K.G",
// lower-case, missing dots). The canonical list is in CLASSES — match a raw value
// against it by stripping non-alphanumerics and comparing case-insensitively.
const normKey = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");
const canonicalizeClass = (raw: string): string => {
  const target = normKey(raw);
  return CLASSES.find((c) => normKey(c) === target) ?? raw;
};
const canonicalizeClassList = (raw: string[]): string[] => raw.map(canonicalizeClass);

function CredentialReveal({ password, employeeId, email }: { password: string; employeeId?: string; email?: string }) {
  const [show, setShow] = useState(true);
  const [copied, setCopied] = useState<string | null>(null);
  const copy = async (text: string, label: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(label);
      setTimeout(() => setCopied(null), 1500);
    } catch {
      toast("Copy failed", "error");
    }
  };
  return (
    <div className="rounded-md border border-emerald-200 bg-emerald-50 p-3 space-y-2">
      <div className="text-xs font-medium text-emerald-800">
        Share these credentials with the staff member — the password won't be visible again.
      </div>
      {email && (
        <div className="flex items-center gap-2">
          <div className="text-xs w-20 text-emerald-800">Email</div>
          <code className="flex-1 font-mono text-sm bg-white border rounded px-3 py-1.5">{email}</code>
          <Button type="button" size="icon" variant="outline" onClick={() => copy(email, "email")} aria-label="Copy email">
            {copied === "email" ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      )}
      {employeeId && (
        <div className="flex items-center gap-2">
          <div className="text-xs w-20 text-emerald-800">Employee ID</div>
          <code className="flex-1 font-mono text-sm bg-white border rounded px-3 py-1.5">{employeeId}</code>
          <Button type="button" size="icon" variant="outline" onClick={() => copy(employeeId, "eid")} aria-label="Copy employee id">
            {copied === "eid" ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
          </Button>
        </div>
      )}
      <div className="flex items-center gap-2">
        <div className="text-xs w-20 text-emerald-800">Password</div>
        <code className="flex-1 font-mono text-lg tracking-wider bg-white border rounded px-3 py-1.5">
          {show ? password : "•".repeat(password.length)}
        </code>
        <Button type="button" size="icon" variant="outline" onClick={() => setShow((s) => !s)} aria-label={show ? "Hide" : "Show"}>
          {show ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
        </Button>
        <Button type="button" size="icon" variant="outline" onClick={() => copy(password, "pw")} aria-label="Copy password">
          {copied === "pw" ? <Check className="h-4 w-4 text-emerald-600" /> : <Copy className="h-4 w-4" />}
        </Button>
      </div>
    </div>
  );
}

export default function StaffPage() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { isSuperAdmin } = useAuth();
  const [importOpen, setImportOpen] = useState(false);
  const [addOpen, setAddOpen] = useState(false);
  const [editing, setEditing] = useState<Staff | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Staff | null>(null);

  const { data = [] } = useQuery<Staff[]>({ queryKey: ["staff"], queryFn: () => api.get("/staff").then((r) => r.data) });
  useSSE("staff", [["staff"]]);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.staff")}</h1>
        <div className="flex items-center gap-2">
          <Button onClick={() => setAddOpen(true)}>
            <Plus className="h-4 w-4" /> Add staff
          </Button>
          <Button variant="outline" onClick={() => setImportOpen(true)}>
            <FileSpreadsheet className="h-4 w-4" /> Bulk import
          </Button>
        </div>
      </div>

      <BulkImportDialog
        open={importOpen}
        onOpenChange={setImportOpen}
        title="Bulk import staff"
        description='One staff per row. Required: name, email. assigned_classes is semicolon-separated (e.g. "5th;6th") or "All". Server auto-generates Employee IDs and initial passwords; the response lists them so you can hand them out.'
        templateCsv={STAFF_TEMPLATE}
        templateFilename="staff-template.csv"
        uploadPath="/staff/bulk-import"
        onSuccess={() => qc.invalidateQueries({ queryKey: ["staff"] })}
      />

      <Card>
        <CardContent className="pt-6">
          <div className="mb-3 text-sm text-muted-foreground">
            Staff directory ({data.length})
          </div>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead>Employee ID</TableHead>
                <TableHead>Designation</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Phone</TableHead>
                <TableHead>Classes</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {data.map((s) => {
                const pending = s.status === "pending_delete";
                const placeholder = isPlaceholderEmail(s.email);
                return (
                  <TableRow key={s.id} className={pending ? "bg-amber-50/60" : undefined}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span>{s.name}</span>
                        {pending && (
                          <Badge variant="warning" className="gap-1">
                            <Clock className="h-3 w-3" /> Deletion requested
                          </Badge>
                        )}
                      </div>
                      {pending && s.delete_reason && (
                        <div className="text-xs text-muted-foreground mt-0.5">Reason: {s.delete_reason}</div>
                      )}
                    </TableCell>
                    <TableCell><code className="text-xs">{s.employee_id}</code></TableCell>
                    <TableCell>{s.designation}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-sm">{s.email}</span>
                        {placeholder && (
                          <Badge variant="warning" className="gap-1">
                            <AlertTriangle className="h-3 w-3" /> Placeholder
                          </Badge>
                        )}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{s.phone || "—"}</TableCell>
                    <TableCell>{canonicalizeClassList(s.assigned_classes).map((c) => <Badge key={c} variant="info" className="mr-1">{c}</Badge>)}</TableCell>
                    <TableCell className="text-right whitespace-nowrap">
                      <Button size="icon" variant="ghost" onClick={() => setEditing(s)} aria-label="Edit">
                        <Pencil className="h-4 w-4" />
                      </Button>
                      {!pending && (
                        <Button
                          size="icon"
                          variant="ghost"
                          className="text-red-600"
                          onClick={() => setDeleteTarget(s)}
                          aria-label={isSuperAdmin ? "Delete" : "Request delete"}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                );
              })}
              {!data.length && <TableRow><TableCell colSpan={7} className="text-center text-muted-foreground py-6">No staff yet</TableCell></TableRow>}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <AddStaffDialog
        open={addOpen}
        onClose={() => setAddOpen(false)}
        onSaved={() => qc.invalidateQueries({ queryKey: ["staff"] })}
      />

      <EditStaffDialog
        staff={editing}
        onClose={() => setEditing(null)}
        onSaved={() => qc.invalidateQueries({ queryKey: ["staff"] })}
      />

      <DeleteStaffDialog
        staff={deleteTarget}
        onClose={() => setDeleteTarget(null)}
        isSuperAdmin={!!isSuperAdmin}
      />
    </div>
  );
}

function DeleteStaffDialog({
  staff,
  onClose,
  isSuperAdmin,
}: {
  staff: Staff | null;
  onClose: () => void;
  isSuperAdmin: boolean;
}) {
  const qc = useQueryClient();
  const [reason, setReason] = useState("");
  const open = !!staff;

  const mut = useMutation({
    mutationFn: () => {
      if (!staff) throw new Error("No staff");
      return api.delete(`/staff/${staff.id}`, { data: { reason: reason || null } });
    },
    onSuccess: () => {
      toast(isSuperAdmin ? "Staff archived" : "Deletion requested for super-admin approval", "warning");
      qc.invalidateQueries({ queryKey: ["staff"] });
      qc.invalidateQueries({ queryKey: ["deletion-requests"] });
      setReason("");
      onClose();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Dialog
      open={open}
      onOpenChange={(o) => {
        if (!o) { setReason(""); onClose(); }
      }}
    >
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{isSuperAdmin ? "Archive staff" : "Request staff deletion"}</DialogTitle>
          <DialogDescription>
            {isSuperAdmin
              ? <>Move <b>{staff?.name}</b> to the archive (recoverable). Use the Pending Deletions page to purge or restore.</>
              : <>Submit <b>{staff?.name}</b> for super-admin approval. The record stays visible with a "Deletion requested" badge until approved.</>}
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          <Label>Reason (optional)</Label>
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="e.g. left school, duplicate record"
            rows={3}
            maxLength={500}
          />
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => { setReason(""); onClose(); }}>Cancel</Button>
          <Button
            variant="destructive"
            disabled={mut.isPending}
            onClick={() => mut.mutate()}
          >
            {mut.isPending ? "Submitting…" : isSuperAdmin ? "Archive" : "Submit request"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AddStaffDialog({ open, onClose, onSaved }: { open: boolean; onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState("");
  const [designation, setDesignation] = useState(DESIGNATIONS[0]);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [classes, setClasses] = useState<string[]>([]);
  const [created, setCreated] = useState<StaffCreateResponse | null>(null);

  useEffect(() => {
    if (open) {
      setName(""); setDesignation(DESIGNATIONS[0]); setPhone(""); setEmail(""); setClasses([]); setCreated(null);
    }
  }, [open]);

  const toggleClass = (c: string) => setClasses((s) => s.includes(c) ? s.filter((x) => x !== c) : [...s, c]);

  const create = useMutation({
    mutationFn: async () => {
      const payload = {
        name: name.trim(),
        designation,
        phone: phone.trim(),
        email: email.trim().toLowerCase(),
        // Collapse "every class ticked" to "All" for storage parity.
        assigned_classes: classes.length === 0 || classes.length === CLASSES.length ? ["All"] : classes,
      };
      const { data } = await api.post<StaffCreateResponse>("/staff", payload);
      return data;
    },
    onSuccess: (data) => {
      toast(`${data.name} added`, "success");
      setCreated(data);
      onSaved();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Add staff member</DialogTitle>
          <DialogDescription>
            Server assigns the Employee ID and an initial password. Both are shown once after submit — share them with the staff member.
          </DialogDescription>
        </DialogHeader>

        {created ? (
          <div className="space-y-3">
            <CredentialReveal
              password={created.initial_password}
              employeeId={created.employee_id}
              email={created.email}
            />
            <DialogFooter>
              <Button onClick={onClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!name.trim()) return toast("Enter name", "warning");
              if (!email.trim()) return toast("Enter email", "warning");
              create.mutate();
            }}
          >
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5"><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} required /></div>
              <div className="space-y-1.5"><Label>Phone</Label><Input value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 15))} inputMode="numeric" /></div>
              <div className="space-y-1.5 col-span-2"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="staff.member@school.org" required /></div>
              <div className="space-y-1.5 col-span-2"><Label>Designation</Label>
                <Select value={designation} onValueChange={setDesignation}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{DESIGNATIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                </Select>
              </div>
            </div>
            <div className="space-y-1.5">
              <Label>Assigned classes (leave empty = All)</Label>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 border rounded-md p-3 bg-muted/30">
                {CLASSES.map((c) => (
                  <label key={c} className="flex items-center gap-1.5 text-sm">
                    <Checkbox checked={classes.includes(c)} onCheckedChange={() => toggleClass(c)} /> {c}
                  </label>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">Selecting every class is equivalent to All.</p>
            </div>
            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={create.isPending}>{create.isPending ? "Adding…" : "Add staff"}</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}

function EditStaffDialog({ staff, onClose, onSaved }: { staff: Staff | null; onClose: () => void; onSaved: () => void }) {
  const open = !!staff;
  const [name, setName] = useState("");
  const [designation, setDesignation] = useState(DESIGNATIONS[0]);
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [classes, setClasses] = useState<string[]>([]);
  const [resetPassword, setResetPassword] = useState(false);
  const [newPassword, setNewPassword] = useState<string | null>(null);

  useEffect(() => {
    if (staff) {
      setName(staff.name);
      setDesignation(staff.designation || DESIGNATIONS[0]);
      setPhone(staff.phone || "");
      setEmail(staff.email || "");
      // ALL-classes fix: when assigned_classes=["All"], tick every checkbox (was: empty).
      // Also canonicalize legacy spellings (e.g. "LKG" → "L.K.G") so they match the
      // checkbox list and pre-tick correctly.
      setClasses(
        staff.assigned_classes.includes("All")
          ? [...CLASSES]
          : canonicalizeClassList(staff.assigned_classes)
      );
      setResetPassword(false);
      setNewPassword(null);
    }
  }, [staff]);

  const toggleClass = (c: string) => setClasses((s) => s.includes(c) ? s.filter((x) => x !== c) : [...s, c]);

  const save = useMutation({
    mutationFn: async () => {
      if (!staff) throw new Error("No staff");
      // Collapse "every class ticked OR none" to "All" for storage parity.
      const assigned = classes.length === 0 || classes.length === CLASSES.length ? ["All"] : classes;
      const body: Record<string, unknown> = {
        name: name.trim(),
        designation,
        phone: phone.trim(),
        email: email.trim().toLowerCase(),
        assigned_classes: assigned,
        reset_password: resetPassword,
      };
      const { data } = await api.patch<StaffUpdateResponse>(`/staff/${staff.id}`, body);
      return data;
    },
    onSuccess: (data) => {
      toast("Staff updated", "success");
      onSaved();
      if (data.new_password) {
        setNewPassword(data.new_password);
      } else {
        onClose();
      }
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Dialog open={open} onOpenChange={(o) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle>Edit staff</DialogTitle>
          <DialogDescription>Update profile, change email, or reset the password.</DialogDescription>
        </DialogHeader>

        {newPassword ? (
          <div className="space-y-3">
            <CredentialReveal password={newPassword} email={email} employeeId={staff?.employee_id} />
            <DialogFooter>
              <Button onClick={onClose}>Done</Button>
            </DialogFooter>
          </div>
        ) : (
          <form
            className="space-y-3"
            onSubmit={(e) => {
              e.preventDefault();
              if (!name.trim()) return toast("Enter name", "warning");
              if (!email.trim()) return toast("Enter email", "warning");
              save.mutate();
            }}
          >
            <div className="grid grid-cols-2 gap-2">
              <div className="space-y-1.5"><Label>Name</Label><Input value={name} onChange={(e) => setName(e.target.value)} required /></div>
              <div className="space-y-1.5"><Label>Phone</Label><Input value={phone} onChange={(e) => setPhone(e.target.value.replace(/\D/g, "").slice(0, 15))} inputMode="numeric" /></div>
              <div className="space-y-1.5 col-span-2"><Label>Email</Label><Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></div>
              <div className="space-y-1.5 col-span-2"><Label>Designation</Label>
                <Select value={designation} onValueChange={setDesignation}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>{DESIGNATIONS.map((d) => <SelectItem key={d} value={d}>{d}</SelectItem>)}</SelectContent>
                </Select>
              </div>
              <div className="space-y-1.5 col-span-2">
                <Label>Employee ID</Label>
                <Input value={staff?.employee_id ?? ""} readOnly className="font-mono bg-muted/30" />
              </div>
            </div>

            <div className="space-y-1.5">
              <Label>Assigned classes (leave empty = All)</Label>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 border rounded-md p-3 bg-muted/30">
                {CLASSES.map((c) => (
                  <label key={c} className="flex items-center gap-1.5 text-sm">
                    <Checkbox checked={classes.includes(c)} onCheckedChange={() => toggleClass(c)} /> {c}
                  </label>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">Selecting every class is equivalent to All.</p>
            </div>

            <div className="space-y-2 rounded-md border p-3">
              <label className="flex items-center gap-2 text-sm font-medium">
                <Checkbox checked={resetPassword} onCheckedChange={(v) => setResetPassword(!!v)} />
                Reset password
              </label>
              <p className="text-xs text-muted-foreground pl-6">
                {resetPassword
                  ? "A new 6-digit password will be generated on save. Share it with the staff member from the next screen."
                  : "Tick to issue a new password. Leave unchecked to keep the existing one."}
              </p>
            </div>

            <DialogFooter>
              <Button type="button" variant="outline" onClick={onClose}>Cancel</Button>
              <Button type="submit" disabled={save.isPending}>{save.isPending ? "Saving…" : "Save"}</Button>
            </DialogFooter>
          </form>
        )}
      </DialogContent>
    </Dialog>
  );
}
