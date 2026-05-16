import { useParams, useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Pencil, Save, ArrowLeft, Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { toast } from "@/components/ui/toaster";
import { api, apiError, fileUrl } from "@/lib/api";
import { CLASSES, RELIGIONS, toTitleCase, digitsOnly, dobBounds, cn } from "@/lib/utils";
import { useAuth } from "@/lib/auth";
import { compressImage } from "@/lib/compress";
import type { Student, DocumentKind } from "@/types/api";

type Errors = Partial<Record<
  "class_name" | "admission_no" | "roll_no" | "name" | "father" | "mother" | "gender" | "dob" | "phone" | "alt_phone" | "aadhar",
  string
>>;

function validate(f: Partial<Student>): Errors {
  const e: Errors = {};
  if (!f.class_name) e.class_name = "Pick a class";
  if (f.admission_no == null) e.admission_no = "Required";
  if (!f.roll_no?.toString().trim()) e.roll_no = "Required";
  if (!f.name?.trim()) e.name = "Required";
  if (!f.father?.trim()) e.father = "Required";
  if (!f.mother?.trim()) e.mother = "Required";
  if (!f.gender) e.gender = "Pick a gender";
  if (!f.dob) e.dob = "Required";
  if (!/^\d{10}$/.test(f.phone ?? "")) e.phone = "Must be exactly 10 digits";
  if (f.alt_phone && f.alt_phone !== "N/A" && !/^\d{10}$/.test(f.alt_phone)) e.alt_phone = "Must be exactly 10 digits";
  if (!/^\d{12}$/.test(f.aadhar ?? "")) e.aadhar = "Must be exactly 12 digits";
  return e;
}

export default function StudentDetail() {
  const { id } = useParams<{ id: string }>();
  const [sp, setSp] = useSearchParams();
  const editing = sp.get("edit") === "1";
  const nav = useNavigate();
  const qc = useQueryClient();
  const { user } = useAuth();

  const { data: s } = useQuery<Student>({
    queryKey: ["student", id],
    queryFn: () => api.get(`/students/${id}`).then((r) => r.data),
    enabled: !!id,
  });

  const [form, setForm] = useState<Partial<Student>>({});
  const [errors, setErrors] = useState<Errors>({});
  useEffect(() => { if (s) { setForm(s); setErrors({}); } }, [s]);

  const save = useMutation({
    mutationFn: () => {
      // Strip read-only fields the API doesn't accept on input.
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      const { admission_id: _ai, ...editable } = form;
      const body = {
        ...editable,
        // Re-apply title case at submit time so even pasted-in names get normalised
        name: editable.name ? toTitleCase(editable.name) : editable.name,
        father: editable.father ? toTitleCase(editable.father) : editable.father,
        mother: editable.mother ? toTitleCase(editable.mother) : editable.mother,
        bank_ifsc: editable.bank_ifsc ? editable.bank_ifsc.toUpperCase() : editable.bank_ifsc,
      };
      return api.patch(`/students/${id}`, body);
    },
    onSuccess: () => {
      toast("Student updated", "success");
      qc.invalidateQueries({ queryKey: ["student", id] });
      qc.invalidateQueries({ queryKey: ["students"] });
      setSp({});
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const uploadDoc = async (kind: DocumentKind, file: File) => {
    const compressed = await compressImage(file);
    const fd = new FormData(); fd.append("file", compressed);
    await api.post(`/students/${id}/documents/${kind}`, fd, { headers: { "Content-Type": "multipart/form-data" } });
    toast(`${kind} uploaded`, "success");
    qc.invalidateQueries({ queryKey: ["student", id] });
  };

  if (!s) return <div className="text-muted-foreground">Loading…</div>;

  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;

  const set = <K extends keyof Student>(k: K, v: Student[K] | undefined) => {
    setForm((x) => ({ ...x, [k]: v }));
    if (errors[k as keyof Errors]) {
      setErrors((e) => ({ ...e, [k]: undefined }));
    }
  };

  const titleCaseOnBlur = (k: "name" | "father" | "mother") => () =>
    set(k, form[k] ? toTitleCase(form[k] as string) : form[k]);

  const handleSave = () => {
    const v = validate(form);
    setErrors(v);
    if (Object.keys(v).length) {
      toast("Please fix the errors highlighted in the form", "warning");
      return;
    }
    save.mutate();
  };

  return (
    <div className="max-w-5xl space-y-4">
      <div className="flex items-center gap-2">
        <Button size="icon" variant="ghost" onClick={() => nav("/students")}><ArrowLeft className="h-4 w-4" /></Button>
        <h1 className="text-2xl font-bold">{s.name}</h1>
        <Badge variant="info">{s.class_name}</Badge>
        <div className="ml-auto">
          {!editing ? (
            <Button onClick={() => setSp({ edit: "1" })}><Pencil className="h-4 w-4" /> Edit</Button>
          ) : (
            <div className="flex gap-2">
              <Button variant="outline" onClick={() => { setForm(s); setErrors({}); setSp({}); }}>Cancel</Button>
              <Button onClick={handleSave} disabled={save.isPending}><Save className="h-4 w-4" /> Save</Button>
            </div>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="lg:col-span-2">
          <CardHeader><CardTitle>Profile</CardTitle></CardHeader>
          <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <F label="Class" required error={errors.class_name}>
              {editing ? (
                <Select value={form.class_name ?? ""} onValueChange={(v) => set("class_name", v)}>
                  <SelectTrigger className={cn(errors.class_name && "border-destructive")}><SelectValue /></SelectTrigger>
                  <SelectContent>{allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
                </Select>
              ) : (<b>{s.class_name}</b>)}
            </F>

            <F label="Admission no." required error={errors.admission_no}>
              {editing ? (
                <Input
                  type="number"
                  min={1}
                  placeholder="e.g. 421"
                  value={form.admission_no ?? ""}
                  onChange={(e) => {
                    const v = digitsOnly(e.target.value);
                    set("admission_no", v ? (Number(v) as Student["admission_no"]) : null);
                  }}
                  className={cn(errors.admission_no && "border-destructive")}
                />
              ) : (<b>{s.admission_no ?? "—"}</b>)}
            </F>
            <F label="Adm. ID (auto)">
              <b className="text-muted-foreground">{s.admission_id ?? "—"}</b>
            </F>
            <F label="Roll no." required error={errors.roll_no}>
              {editing ? (
                <Input
                  placeholder="e.g. 14"
                  value={form.roll_no ?? ""}
                  onChange={(e) => set("roll_no", (e.target.value || null) as Student["roll_no"])}
                  className={cn(errors.roll_no && "border-destructive")}
                />
              ) : (<b>{s.roll_no ?? "—"}</b>)}
            </F>

            <F label="Name" required error={errors.name}>
              {editing ? (
                <Input
                  value={form.name ?? ""}
                  onChange={(e) => set("name", e.target.value)}
                  onBlur={titleCaseOnBlur("name")}
                  className={cn(errors.name && "border-destructive")}
                />
              ) : (<b>{s.name}</b>)}
            </F>
            <F label="Father" required error={errors.father}>
              {editing ? (
                <Input
                  value={form.father ?? ""}
                  onChange={(e) => set("father", e.target.value)}
                  onBlur={titleCaseOnBlur("father")}
                  className={cn(errors.father && "border-destructive")}
                />
              ) : (<b>{s.father}</b>)}
            </F>
            <F label="Mother" required error={errors.mother}>
              {editing ? (
                <Input
                  value={form.mother ?? ""}
                  onChange={(e) => set("mother", e.target.value)}
                  onBlur={titleCaseOnBlur("mother")}
                  className={cn(errors.mother && "border-destructive")}
                />
              ) : (<b>{s.mother}</b>)}
            </F>

            <F label="DOB" required error={errors.dob}>
              {editing ? (
                <DatePicker
                  value={form.dob ?? ""}
                  onChange={(iso) => set("dob", iso)}
                  min={dobBounds().min}
                  max={dobBounds().max}
                  className={cn(errors.dob && "border-destructive")}
                />
              ) : (<b>{s.dob ?? "—"}</b>)}
            </F>
            <F label="Gender" required error={errors.gender}>
              {editing ? (
                <Select value={form.gender ?? ""} onValueChange={(v) => set("gender", v)}>
                  <SelectTrigger className={cn(errors.gender && "border-destructive")}><SelectValue placeholder="Select" /></SelectTrigger>
                  <SelectContent>
                    {["Male", "Female", "Other"].map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                  </SelectContent>
                </Select>
              ) : (<b>{s.gender || "—"}</b>)}
            </F>

            <F label="Village">{editing ? <Input value={form.village ?? ""} onChange={(e) => set("village", e.target.value)} /> : <b>{s.village || "—"}</b>}</F>

            <F label="Phone (10 digits)" required error={errors.phone}>
              {editing ? (
                <Input
                  inputMode="numeric"
                  pattern="\d{10}"
                  maxLength={10}
                  value={form.phone ?? ""}
                  onChange={(e) => set("phone", digitsOnly(e.target.value).slice(0, 10))}
                  className={cn(errors.phone && "border-destructive")}
                />
              ) : (<b>{s.phone || "—"}</b>)}
            </F>

            <F label="Alt phone (10 digits)" error={errors.alt_phone}>
              {editing ? (
                <Input
                  inputMode="numeric"
                  pattern="\d{10}"
                  maxLength={10}
                  value={form.alt_phone === "N/A" ? "" : form.alt_phone ?? ""}
                  onChange={(e) => set("alt_phone", digitsOnly(e.target.value).slice(0, 10) || "N/A")}
                  className={cn(errors.alt_phone && "border-destructive")}
                />
              ) : (<b>{s.alt_phone}</b>)}
            </F>

            <F label="Aadhaar (12 digits)" required error={errors.aadhar}>
              {editing ? (
                <Input
                  inputMode="numeric"
                  pattern="\d{12}"
                  maxLength={12}
                  value={form.aadhar ?? ""}
                  onChange={(e) => set("aadhar", digitsOnly(e.target.value).slice(0, 12))}
                  className={cn(errors.aadhar && "border-destructive")}
                />
              ) : (<b>{s.aadhar || "—"}</b>)}
            </F>

            <F label="Religion">
              {editing ? (
                <Select
                  value={form.religion === "N/A" ? "" : form.religion ?? ""}
                  onValueChange={(v) => set("religion", v || "N/A")}
                >
                  <SelectTrigger><SelectValue placeholder="Select religion" /></SelectTrigger>
                  <SelectContent>
                    {RELIGIONS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                  </SelectContent>
                </Select>
              ) : (<b>{s.religion}</b>)}
            </F>

            <F label="Prev school">{editing ? <Input value={form.prev_school === "N/A" ? "" : form.prev_school ?? ""} onChange={(e) => set("prev_school", e.target.value || "N/A")} /> : <b>{s.prev_school}</b>}</F>
            <F label="Bank">{editing ? <Input value={form.bank_name === "N/A" ? "" : form.bank_name ?? ""} onChange={(e) => set("bank_name", e.target.value || "N/A")} /> : <b>{s.bank_name}</b>}</F>
            <F label="A/c no">
              {editing ? (
                <Input
                  inputMode="numeric"
                  value={form.bank_acc === "N/A" ? "" : form.bank_acc ?? ""}
                  onChange={(e) => set("bank_acc", digitsOnly(e.target.value) || "N/A")}
                />
              ) : (<b>{s.bank_acc}</b>)}
            </F>
            <F label="IFSC">{editing ? <Input value={form.bank_ifsc === "N/A" ? "" : form.bank_ifsc ?? ""} onChange={(e) => set("bank_ifsc", e.target.value.toUpperCase() || "N/A")} /> : <b>{s.bank_ifsc}</b>}</F>
            <F label="Annual fee">
              {editing ? (
                <Input
                  type="number"
                  min={0}
                  step={1}
                  placeholder="0"
                  // Empty input when 0 so the user doesn't have to delete a leading zero.
                  value={Number(form.annual_fee ?? 0) > 0 ? String(form.annual_fee) : ""}
                  onChange={(e) => set("annual_fee", digitsOnly(e.target.value) as unknown as Student["annual_fee"])}
                />
              ) : (<b>₹{s.annual_fee}</b>)}
            </F>
          </CardContent>
        </Card>

        <Card>
          <CardHeader><CardTitle>Documents</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <DocSlot label="Photo" sid={s.id} kind="photo" present={s.has_photo} onUpload={(f) => uploadDoc("photo", f)} />
            <DocSlot label="DOB certificate" sid={s.id} kind="dob_cert" present={s.has_dob_cert} onUpload={(f) => uploadDoc("dob_cert", f)} />
            <DocSlot label="Aadhaar" sid={s.id} kind="aadhar" present={s.has_aadhar} onUpload={(f) => uploadDoc("aadhar", f)} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function F({ label, error, required, children }: { label: string; error?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <Label className="text-xs text-muted-foreground">
        {label}
        {required && <span className="text-destructive ml-0.5" aria-hidden="true">*</span>}
      </Label>
      <div className="mt-1">{children}</div>
      {error && <p className="text-xs text-destructive mt-1">{error}</p>}
    </div>
  );
}

function DocSlot({ label, sid, kind, present, onUpload }: { label: string; sid: number; kind: DocumentKind; present: boolean; onUpload: (f: File) => void }) {
  return (
    <div className="space-y-2">
      <Label className="text-sm">{label}</Label>
      {present && kind === "photo" && (
        <img src={fileUrl(sid, "photo")} alt="Student" className="h-24 w-24 object-cover rounded" />
      )}
      {present && kind !== "photo" && (
        <a href={fileUrl(sid, kind)} target="_blank" rel="noreferrer" className="text-sm text-blue-600 underline block">Open uploaded {label.toLowerCase()}</a>
      )}
      <label className="block border border-dashed rounded p-3 text-center text-xs cursor-pointer hover:bg-muted/40">
        <Upload className="h-4 w-4 mx-auto mb-1" />
        {present ? "Replace" : "Upload"} {label.toLowerCase()}
        <input type="file" className="hidden" accept="image/*,application/pdf" onChange={(e) => { const f = e.target.files?.[0]; if (f) onUpload(f); }} />
      </label>
    </div>
  );
}
