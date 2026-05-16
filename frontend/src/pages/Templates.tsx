import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, Trash2, Pencil, FileText, ScrollText } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { CLASSES } from "@/lib/utils";
import type { PdfTemplate, PdfTemplateKind } from "@/types/api";

const KIND_LABEL: Record<PdfTemplateKind, string> = {
  "report-card": "Report Card",
  "pseb-admit-card": "PSEB Admit Card",
};

const KIND_ICON: Record<PdfTemplateKind, typeof FileText> = {
  "report-card": FileText,
  "pseb-admit-card": ScrollText,
};

export default function Templates() {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const nav = useNavigate();
  const [newOpen, setNewOpen] = useState(false);

  const { data = [], isLoading } = useQuery<PdfTemplate[]>({
    queryKey: ["pdf-templates"],
    queryFn: () => api.get("/pdf/templates").then((r) => r.data),
  });

  const del = useMutation({
    mutationFn: (id: number) => api.delete(`/pdf/templates/${id}`),
    onSuccess: () => {
      toast("Template deleted", "warning");
      qc.invalidateQueries({ queryKey: ["pdf-templates"] });
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <h1 className="font-display text-heading-lg text-deep-indigo">{t("portal.nav.templates", "Templates")}</h1>
        <Button onClick={() => setNewOpen(true)}><Plus className="h-4 w-4" /> New template</Button>
      </div>
      <p className="text-sm text-muted-foreground">
        Save class-level template config (centre, exam time, signatures, grading scale, …) once, then bulk-generate
        report cards or PSEB admit cards for every student in that class. Editing a template invalidates cached PDFs.
      </p>

      <Card>
        <CardHeader><CardTitle>Saved templates ({data.length})</CardTitle></CardHeader>
        <CardContent>
          {isLoading ? (
            <p className="text-muted-foreground text-sm">Loading…</p>
          ) : !data.length ? (
            <p className="text-muted-foreground text-sm">No templates yet. Click <b>New template</b> above to create one.</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Kind</TableHead>
                  <TableHead>Class</TableHead>
                  <TableHead>Session</TableHead>
                  <TableHead>Term</TableHead>
                  <TableHead>Version</TableHead>
                  <TableHead>Last updated</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {data.map((row) => {
                  const Icon = KIND_ICON[row.kind];
                  return (
                    <TableRow key={row.id}>
                      <TableCell>
                        <span className="inline-flex items-center gap-2">
                          <Icon className="h-4 w-4 text-khalsa-blue" />
                          {KIND_LABEL[row.kind]}
                        </span>
                      </TableCell>
                      <TableCell><Badge variant="info">{row.class_name}</Badge></TableCell>
                      <TableCell>{row.session}</TableCell>
                      <TableCell>{row.term ?? "—"}</TableCell>
                      <TableCell><code className="text-xs">v{row.version}</code></TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {new Date(row.updated_at).toLocaleString()}<br />
                        <span>by {row.updated_by || "—"}</span>
                      </TableCell>
                      <TableCell className="text-right whitespace-nowrap">
                        <Button size="icon" variant="ghost" onClick={() => nav(`/templates/${row.id}`)} aria-label="Open">
                          <Pencil className="h-4 w-4" />
                        </Button>
                        <Button size="icon" variant="ghost" className="text-red-600" onClick={() => confirm(`Delete this ${KIND_LABEL[row.kind]} template? Cached PDFs will be removed too.`) && del.mutate(row.id)} aria-label="Delete">
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <NewTemplateDialog open={newOpen} onOpenChange={setNewOpen} />
    </div>
  );
}

function NewTemplateDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (b: boolean) => void }) {
  const nav = useNavigate();
  const qc = useQueryClient();
  const currentYear = new Date().getFullYear();
  const defaultSession = `${currentYear}-${String((currentYear + 1) % 100).padStart(2, "0")}`;

  const [kind, setKind] = useState<PdfTemplateKind>("report-card");
  const [klass, setKlass] = useState<string>("");
  const [session, setSession] = useState<string>(defaultSession);
  const [term, setTerm] = useState<string>("Term II");

  const create = useMutation({
    mutationFn: () => {
      // Seed a minimal valid `data` payload per kind so the schema validates.
      const seed = kind === "report-card"
        ? { signatures: { principal: "Gurpreet Singh" }, coScholasticHeads: [] }
        : {
            schoolCode: "0098351",
            centre: { code: "", schoolCode: "", district: "", set: "", name: { en: "", pa: "" } },
            examTime: { en: "", pa: "" },
            dateSheet: [{ subCode: "", subject: { en: "", pa: "" }, theoryDate: "", practical: "No" }],
            instructions: [],
          };
      return api.post<PdfTemplate>("/pdf/templates", {
        kind,
        class_name: klass,
        session,
        term: kind === "report-card" ? term : null,
        data: seed,
      });
    },
    onSuccess: ({ data }) => {
      toast("Template created", "success");
      qc.invalidateQueries({ queryKey: ["pdf-templates"] });
      onOpenChange(false);
      nav(`/templates/${data.id}`);
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>New template</DialogTitle>
          <DialogDescription>Pick a kind and the class scope. You'll fill in the details on the next screen.</DialogDescription>
        </DialogHeader>
        <form onSubmit={(e) => { e.preventDefault(); if (!klass) return toast("Pick a class", "warning"); create.mutate(); }} className="space-y-3">
          <div className="space-y-1.5">
            <Label>Kind</Label>
            <Select value={kind} onValueChange={(v) => setKind(v as PdfTemplateKind)}>
              <SelectTrigger><SelectValue /></SelectTrigger>
              <SelectContent>
                <SelectItem value="report-card">Report Card</SelectItem>
                <SelectItem value="pseb-admit-card">PSEB Admit Card</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Class</Label>
            <Select value={klass} onValueChange={setKlass}>
              <SelectTrigger><SelectValue placeholder="Select class" /></SelectTrigger>
              <SelectContent>{CLASSES.map((c) => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
            </Select>
          </div>
          <div className="space-y-1.5">
            <Label>Session</Label>
            <Input value={session} onChange={(e) => setSession(e.target.value)} placeholder="2025-26" />
          </div>
          {kind === "report-card" && (
            <div className="space-y-1.5">
              <Label>Term</Label>
              <Input value={term} onChange={(e) => setTerm(e.target.value)} placeholder="Term II" />
            </div>
          )}
          <DialogFooter>
            <Button type="button" variant="outline" onClick={() => onOpenChange(false)}>Cancel</Button>
            <Button type="submit" disabled={create.isPending}>{create.isPending ? "Creating…" : "Create"}</Button>
          </DialogFooter>
        </form>
        <p className="text-xs text-muted-foreground">
          You can also create one from the <Link to="/templates" className="underline">Templates</Link> list page.
        </p>
      </DialogContent>
    </Dialog>
  );
}
