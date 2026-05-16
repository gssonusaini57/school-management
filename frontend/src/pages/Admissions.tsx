import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { UserPlus, Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { DatePicker } from "@/components/ui/date-picker";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { CLASSES, RELIGIONS, toTitleCase, digitsOnly, dobBounds, cn } from "@/lib/utils";
import type { Student, DocumentKind } from "@/types/api";
import { compressImage } from "@/lib/compress";

const initial = {
  class_name: "", name: "", father: "", mother: "", dob: "", gender: "",
  village: "", phone: "", aadhar: "", alt_phone: "", religion: "", prev_school: "",
  // annual_fee kept as a string so the input can be empty until the user types.
  // Converted to a number at submit time (empty → 0).
  bank_name: "", bank_acc: "", bank_ifsc: "", annual_fee: "",
  // admission_no kept as a string for empty-input UX; converted to int at submit.
  admission_no: "", roll_no: "",
};

type Form = typeof initial;
type Errors = Partial<Record<keyof Form, string>>;

function validate(f: Form): Errors {
  const e: Errors = {};
  if (!f.class_name) e.class_name = "Pick a class";
  if (!f.admission_no || !/^\d+$/.test(f.admission_no)) e.admission_no = "Required";
  if (!f.roll_no.trim()) e.roll_no = "Required";
  if (!f.name.trim()) e.name = "Required";
  if (!f.father.trim()) e.father = "Required";
  if (!f.mother.trim()) e.mother = "Required";
  if (!f.gender) e.gender = "Pick a gender";
  if (!f.dob) e.dob = "Required";
  if (!/^\d{10}$/.test(f.phone)) e.phone = "Must be exactly 10 digits";
  if (f.alt_phone && !/^\d{10}$/.test(f.alt_phone)) e.alt_phone = "Must be exactly 10 digits";
  if (!/^\d{12}$/.test(f.aadhar)) e.aadhar = "Must be exactly 12 digits";
  return e;
}

export default function Admissions() {
  const { t } = useTranslation();
  const { user } = useAuth();
  // Admin has empty allowed_classes (full access) → show all CLASSES.
  // Staff with assigned_classes shows only those.
  const allowed = user?.allowed_classes?.length ? user.allowed_classes : CLASSES;
  const qc = useQueryClient();
  const [form, setForm] = useState<Form>(initial);
  const [errors, setErrors] = useState<Errors>({});
  const [photo, setPhoto] = useState<File | null>(null);
  const [dobCert, setDobCert] = useState<File | null>(null);
  const [aadharFile, setAadharFile] = useState<File | null>(null);
  const [pct, setPct] = useState(0);
  const [uploading, setUploading] = useState(false);

  const upload = async (sid: number, kind: DocumentKind, file: File, onPct: (n: number) => void) => {
    const compressed = await compressImage(file);
    const fd = new FormData();
    fd.append("file", compressed);
    await api.post(`/students/${sid}/documents/${kind}`, fd, {
      headers: { "Content-Type": "multipart/form-data" },
      onUploadProgress: (p) => p.total && onPct(Math.round((p.loaded / p.total) * 100)),
    });
  };

  const create = useMutation({
    mutationFn: async () => {
      const body = {
        ...form,
        // Re-apply title case at submit time so even pasted-in names get normalised
        name: toTitleCase(form.name),
        father: toTitleCase(form.father),
        mother: toTitleCase(form.mother),
        annual_fee: Number(form.annual_fee) || 0,
        alt_phone: form.alt_phone || "N/A",
        religion: form.religion || "N/A",
        prev_school: form.prev_school || "N/A",
        bank_name: form.bank_name || "N/A",
        bank_acc: form.bank_acc || "N/A",
        bank_ifsc: (form.bank_ifsc || "N/A").toUpperCase(),
        admission_no: form.admission_no ? Number(form.admission_no) : null,
        roll_no: form.roll_no.trim() || null,
      };
      const { data: s } = await api.post<Student>("/students", body);

      const files: [DocumentKind, File | null][] = [["photo", photo], ["dob_cert", dobCert], ["aadhar", aadharFile]];
      const active = files.filter(([, f]) => !!f) as [DocumentKind, File][];
      if (active.length) {
        setUploading(true);
        const prog: Record<string, number> = {};
        await Promise.all(
          active.map(([k, f]) =>
            upload(s.id, k, f, (n) => {
              prog[k] = n;
              const total = active.reduce((a, [kk]) => a + (prog[kk] ?? 0), 0) / active.length;
              setPct(Math.round(total));
            })
          )
        );
        setUploading(false);
        setPct(100);
      }
      return s;
    },
    onSuccess: () => {
      toast("Student saved", "success");
      setForm(initial);
      setErrors({});
      setPhoto(null); setDobCert(null); setAadharFile(null); setPct(0);
      qc.invalidateQueries({ queryKey: ["students"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const set = <K extends keyof Form>(k: K, v: Form[K]) => {
    setForm((s) => ({ ...s, [k]: v }));
    if (errors[k]) setErrors((e) => ({ ...e, [k]: undefined }));
  };

  // Title-case on blur for name fields — non-disruptive while typing
  const titleCaseOnBlur = (k: "name" | "father" | "mother") => () =>
    set(k, toTitleCase(form[k]));

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    const v = validate(form);
    setErrors(v);
    if (Object.keys(v).length) {
      toast("Please fix the errors highlighted in the form", "warning");
      return;
    }
    if (!allowed.includes(form.class_name)) return toast("Not authorized for class: " + form.class_name, "error");
    create.mutate();
  };

  // Disable submit when there are unresolved errors after a first attempt
  const submitDisabled = useMemo(
    () => create.isPending || Object.values(errors).some(Boolean),
    [create.isPending, errors]
  );

  return (
    <div className="max-w-5xl space-y-6">
      <h1 className="font-display text-heading-lg text-deep-indigo flex items-center gap-2">
        <UserPlus className="h-6 w-6" /> {t("portal.nav.newAdmission")}
      </h1>
      <Card>
        <CardHeader><CardTitle>Student details</CardTitle></CardHeader>
        <CardContent>
          <form className="grid grid-cols-1 md:grid-cols-3 gap-4" onSubmit={submit}>
            <Field label="Class" required error={errors.class_name}>
              <Select value={form.class_name} onValueChange={(v) => set("class_name", v)}>
                <SelectTrigger className={cn(errors.class_name && "border-destructive")}><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>
                  {allowed.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Admission no." required error={errors.admission_no}>
              <Input
                type="number"
                min={1}
                placeholder="e.g. 421"
                value={form.admission_no}
                onChange={(e) => set("admission_no", digitsOnly(e.target.value))}
                className={cn(errors.admission_no && "border-destructive")}
              />
            </Field>
            <Field label="Roll no." required error={errors.roll_no}>
              <Input
                placeholder="e.g. 14"
                value={form.roll_no}
                onChange={(e) => set("roll_no", e.target.value)}
                className={cn(errors.roll_no && "border-destructive")}
              />
            </Field>

            <Field label="Student name" required error={errors.name}>
              <Input
                value={form.name}
                onChange={(e) => set("name", e.target.value)}
                onBlur={titleCaseOnBlur("name")}
                placeholder="e.g. Arjun Singh"
                className={cn(errors.name && "border-destructive")}
              />
            </Field>
            <Field label="Father's name" required error={errors.father}>
              <Input
                value={form.father}
                onChange={(e) => set("father", e.target.value)}
                onBlur={titleCaseOnBlur("father")}
                className={cn(errors.father && "border-destructive")}
              />
            </Field>
            <Field label="Mother's name" required error={errors.mother}>
              <Input
                value={form.mother}
                onChange={(e) => set("mother", e.target.value)}
                onBlur={titleCaseOnBlur("mother")}
                className={cn(errors.mother && "border-destructive")}
              />
            </Field>

            <Field label="Date of birth" required error={errors.dob}>
              <DatePicker
                value={form.dob}
                onChange={(iso) => set("dob", iso)}
                min={dobBounds().min}
                max={dobBounds().max}
                className={cn(errors.dob && "border-destructive")}
              />
            </Field>

            <Field label="Gender" required error={errors.gender}>
              <Select value={form.gender} onValueChange={(v) => set("gender", v)}>
                <SelectTrigger className={cn(errors.gender && "border-destructive")}><SelectValue placeholder="Select" /></SelectTrigger>
                <SelectContent>
                  {["Male", "Female", "Other"].map((g) => <SelectItem key={g} value={g}>{g}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Village / address">
              <Input value={form.village} onChange={(e) => set("village", e.target.value)} />
            </Field>

            <Field label="Phone (10 digits)" required error={errors.phone}>
              <Input
                inputMode="numeric"
                pattern="\d{10}"
                maxLength={10}
                value={form.phone}
                onChange={(e) => set("phone", digitsOnly(e.target.value).slice(0, 10))}
                className={cn(errors.phone && "border-destructive")}
                placeholder="9876543210"
              />
            </Field>

            <Field label="Aadhaar (12 digits)" required error={errors.aadhar}>
              <Input
                inputMode="numeric"
                pattern="\d{12}"
                maxLength={12}
                value={form.aadhar}
                onChange={(e) => set("aadhar", digitsOnly(e.target.value).slice(0, 12))}
                className={cn(errors.aadhar && "border-destructive")}
                placeholder="123456789012"
              />
            </Field>

            <Field label="Alt phone (10 digits)" error={errors.alt_phone}>
              <Input
                inputMode="numeric"
                pattern="\d{10}"
                maxLength={10}
                value={form.alt_phone}
                onChange={(e) => set("alt_phone", digitsOnly(e.target.value).slice(0, 10))}
                className={cn(errors.alt_phone && "border-destructive")}
              />
            </Field>

            <Field label="Religion">
              <Select value={form.religion} onValueChange={(v) => set("religion", v)}>
                <SelectTrigger><SelectValue placeholder="Select religion" /></SelectTrigger>
                <SelectContent>
                  {RELIGIONS.map((r) => <SelectItem key={r} value={r}>{r}</SelectItem>)}
                </SelectContent>
              </Select>
            </Field>

            <Field label="Previous school">
              <Input value={form.prev_school} onChange={(e) => set("prev_school", e.target.value)} />
            </Field>

            <Field label="Bank name">
              <Input value={form.bank_name} onChange={(e) => set("bank_name", e.target.value)} />
            </Field>
            <Field label="Account no">
              <Input
                inputMode="numeric"
                value={form.bank_acc}
                onChange={(e) => set("bank_acc", digitsOnly(e.target.value))}
              />
            </Field>
            <Field label="IFSC">
              <Input value={form.bank_ifsc} onChange={(e) => set("bank_ifsc", e.target.value.toUpperCase())} />
            </Field>
            <Field label="Annual fee (₹)">
              <Input
                type="number"
                min={0}
                step={1}
                placeholder="0"
                value={form.annual_fee}
                onChange={(e) => set("annual_fee", digitsOnly(e.target.value))}
              />
            </Field>

            <div className="md:col-span-3 grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
              <FileSlot label="Photo" file={photo} onChange={setPhoto} accept="image/*" />
              <FileSlot label="DOB certificate" file={dobCert} onChange={setDobCert} accept="image/*,application/pdf" />
              <FileSlot label="Aadhaar" file={aadharFile} onChange={setAadharFile} accept="image/*,application/pdf" />
            </div>

            {(uploading || pct > 0) && (
              <div className="md:col-span-3">
                <div className="flex justify-between text-xs mb-1">
                  <span>Uploading documents…</span><span>{pct}%</span>
                </div>
                <div className="h-1.5 bg-muted rounded">
                  <div className="h-full bg-emerald-500 rounded transition-all" style={{ width: pct + "%" }} />
                </div>
              </div>
            )}

            <div className="md:col-span-3 flex gap-2">
              <Button type="submit" disabled={submitDisabled}>
                {create.isPending ? "Saving…" : "Save admission"}
              </Button>
              <Button type="button" variant="outline" onClick={() => { setForm(initial); setErrors({}); }}>
                Reset
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function Field({ label, error, required, children }: { label: string; error?: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div className="space-y-1.5">
      <Label>
        {label}
        {required && <span className="text-destructive ml-0.5" aria-hidden="true">*</span>}
      </Label>
      {children}
      {error && <p className="text-xs text-destructive mt-1">{error}</p>}
    </div>
  );
}

function FileSlot({ label, file, onChange, accept }: { label: string; file: File | null; onChange: (f: File | null) => void; accept: string }) {
  return (
    <label className="block border-2 border-dashed rounded-md p-4 text-center cursor-pointer hover:bg-muted/40">
      <Upload className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
      <div className="text-sm font-medium">{label}</div>
      <div className="text-xs text-muted-foreground truncate">{file?.name ?? "Click to choose"}</div>
      <input type="file" className="hidden" accept={accept} onChange={(e) => onChange(e.target.files?.[0] ?? null)} />
    </label>
  );
}
