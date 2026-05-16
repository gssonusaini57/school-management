import { useState } from "react";
import { Upload, Download, FileSpreadsheet, AlertCircle, CheckCircle2, XCircle } from "lucide-react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { api, apiError } from "@/lib/api";
import { toast } from "@/components/ui/toaster";

interface ImportError {
  row: number;
  /** CSV column name that failed validation. null when the error isn't tied
   * to a specific column (e.g. unexpected DB constraint). */
  field?: string | null;
  /** The offending cell value for `field`, when present. */
  value?: string | null;
  reason: string;
  data: Record<string, string>;
}
interface ImportResult {
  inserted: number;
  errors: ImportError[];
  /** True when the backend rejected the whole file (any row failed). */
  aborted?: boolean;
}

interface Props {
  /** Dialog title (e.g. "Bulk import students") */
  title: string;
  /** Body text shown above the file picker */
  description?: string;
  /** Static CSV content for the template download */
  templateCsv: string;
  /** Filename used when downloading the template */
  templateFilename: string;
  /** API path under /api (e.g. "/students/bulk-import") */
  uploadPath: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** Called after a successful import (insert > 0). Use to invalidate queries. */
  onSuccess?: (result: ImportResult) => void;
}

export function BulkImportDialog({
  title,
  description,
  templateCsv,
  templateFilename,
  uploadPath,
  open,
  onOpenChange,
  onSuccess,
}: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [result, setResult] = useState<ImportResult | null>(null);
  // Top-level upload error (network failure, 4xx, 5xx, malformed CSV) — shown
  // inline in the dialog so the user can read and act on it.
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const downloadCsv = (content: string, filename: string) => {
    const blob = new Blob([content], { type: "text/csv;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadTemplate = () => downloadCsv(templateCsv, templateFilename);

  const upload = async () => {
    if (!file) return;
    setBusy(true);
    setResult(null);
    setUploadError(null);

    // Pre-flight: empty file
    if (file.size === 0) {
      setUploadError("The file is empty. Pick a CSV with at least the header row + one data row.");
      setBusy(false);
      return;
    }
    // Pre-flight: looks like CSV?
    if (!/\.csv$/i.test(file.name) && file.type !== "text/csv" && file.type !== "application/vnd.ms-excel") {
      setUploadError(`This doesn't look like a CSV file (${file.name}). Save your spreadsheet as CSV first.`);
      setBusy(false);
      return;
    }

    try {
      const fd = new FormData();
      fd.append("file", file);
      const { data } = await api.post<ImportResult>(uploadPath, fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResult(data);
      if (data.inserted > 0) {
        toast(`Imported ${data.inserted} row${data.inserted === 1 ? "" : "s"}`, "success");
        onSuccess?.(data);
      }
      if (data.errors.length > 0) {
        toast(
          `${data.errors.length} row${data.errors.length === 1 ? "" : "s"} failed — nothing was saved. Fix the errors below and re-upload.`,
          "warning"
        );
      }
      if (data.inserted === 0 && data.errors.length === 0) {
        setUploadError("The CSV had a header row but no data rows. Add at least one row and re-upload.");
      }
    } catch (e) {
      // Surface the backend / network error inline in the dialog so the user
      // can read it. Toast is a backup since it auto-dismisses.
      const msg = apiError(e);
      setUploadError(msg);
      toast(msg, "error");
    } finally {
      setBusy(false);
    }
  };

  const downloadErrors = () => {
    if (!result?.errors.length) return;
    const dataKeys = Array.from(
      new Set(result.errors.flatMap((e) => Object.keys(e.data)))
    );
    const headers = ["row", "field", "value", "reason", ...dataKeys];
    const escape = (v: string) => `"${(v ?? "").replace(/"/g, '""')}"`;
    const lines = [headers.join(",")];
    result.errors.forEach((e) => {
      lines.push(
        [
          e.row,
          escape(e.field ?? ""),
          escape(e.value ?? ""),
          escape(e.reason),
          ...dataKeys.map((k) => escape(e.data[k] ?? "")),
        ].join(",")
      );
    });
    downloadCsv(lines.join("\n"), "import-errors.csv");
  };

  const close = () => {
    setFile(null);
    setResult(null);
    setUploadError(null);
    onOpenChange(false);
  };

  const aborted = !!result && (result.aborted || (result.errors.length > 0 && result.inserted === 0));

  return (
    <Dialog open={open} onOpenChange={(o) => (o ? onOpenChange(o) : close())}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <FileSpreadsheet className="h-5 w-5" /> {title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-3 text-sm">
          {description && <p className="text-muted-foreground">{description}</p>}

          <div className="bg-muted/40 border rounded-md p-3 text-xs">
            <div className="font-semibold mb-1">How it works</div>
            <ol className="list-decimal pl-5 space-y-0.5 text-muted-foreground">
              <li>Download the template CSV.</li>
              <li>Open it in Excel / Google Sheets, fill in your rows, save as CSV.</li>
              <li>Pick the file below and click <b>Upload</b>.</li>
              <li><b>All-or-nothing:</b> if any row fails validation, nothing is saved — fix the errors and re-upload.</li>
            </ol>
          </div>

          <Button variant="outline" onClick={downloadTemplate} className="w-full">
            <Download className="h-4 w-4" /> Download template
          </Button>

          <label className="block border-2 border-dashed rounded-md p-4 text-center cursor-pointer hover:bg-muted/40">
            <Upload className="h-5 w-5 mx-auto mb-1 text-muted-foreground" />
            <div className="font-medium">Choose CSV file</div>
            <div className="text-xs text-muted-foreground truncate">
              {file ? `${file.name} · ${(file.size / 1024).toFixed(1)} KB` : "Click to select"}
            </div>
            <input
              type="file"
              className="hidden"
              accept=".csv,text/csv,application/vnd.ms-excel"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null);
                setResult(null);
                setUploadError(null);
              }}
            />
          </label>

          {/* Top-level error banner (network / HTTP / pre-flight failure) */}
          {uploadError && (
            <div className="border border-red-300 bg-red-50 rounded-md p-3 flex gap-2 items-start">
              <XCircle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
              <div className="space-y-1 min-w-0 flex-1">
                <div className="font-semibold text-red-700">Upload failed</div>
                <div className="text-red-700 break-words">{uploadError}</div>
                <div className="text-xs text-red-600/80 mt-1">
                  Fix the file (or your connection) and click Upload again — no need to close this dialog.
                </div>
              </div>
            </div>
          )}

          {/* Per-row results panel */}
          {result && (
            <div className="border rounded-md p-3 space-y-3">
              {aborted ? (
                <div className="flex items-start gap-2 text-red-700">
                  <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
                  <div>
                    <div className="font-semibold">Nothing was saved.</div>
                    <div className="text-xs text-red-700/90">
                      {result.errors.length} row{result.errors.length === 1 ? "" : "s"} failed validation.
                      Fix the highlighted fields in your CSV and click <b>Try again</b>.
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-emerald-600 font-semibold">
                  <CheckCircle2 className="h-4 w-4" />
                  Inserted: {result.inserted}
                </div>
              )}

              {result.errors.length > 0 && (
                <div className="border-t pt-3 space-y-2">
                  <div className="flex items-center gap-2 text-red-600 font-semibold">
                    <AlertCircle className="h-4 w-4" />
                    {result.errors.length} row{result.errors.length === 1 ? "" : "s"} need fixing
                  </div>

                  <div className="border rounded overflow-hidden">
                    <div className="max-h-64 overflow-auto">
                      <table className="w-full text-xs">
                        <thead className="bg-muted sticky top-0">
                          <tr>
                            <th className="text-left px-2 py-1.5 font-semibold w-12">Row</th>
                            <th className="text-left px-2 py-1.5 font-semibold w-32">Field</th>
                            <th className="text-left px-2 py-1.5 font-semibold w-40">Value</th>
                            <th className="text-left px-2 py-1.5 font-semibold">Reason</th>
                          </tr>
                        </thead>
                        <tbody>
                          {result.errors.slice(0, 50).map((e, i) => {
                            const field = e.field ?? guessField(e);
                            const value = e.value ?? (field ? e.data[field] : "") ?? "";
                            return (
                              <tr key={i} className="border-t">
                                <td className="px-2 py-1.5 font-mono align-top">{e.row}</td>
                                <td className="px-2 py-1.5 align-top">
                                  {field ? (
                                    <code className="bg-red-100 text-red-800 rounded px-1.5 py-0.5">{field}</code>
                                  ) : (
                                    <span className="text-muted-foreground">—</span>
                                  )}
                                </td>
                                <td className="px-2 py-1.5 align-top break-all text-muted-foreground">
                                  {value === "" ? <em>(empty)</em> : <code>{String(value)}</code>}
                                </td>
                                <td className="px-2 py-1.5 text-red-700 align-top">{e.reason}</td>
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    </div>
                    {result.errors.length > 50 && (
                      <div className="text-xs text-muted-foreground bg-muted/40 px-2 py-1 border-t">
                        … {result.errors.length - 50} more rows. Download the report for the full list.
                      </div>
                    )}
                  </div>

                  <Button variant="outline" size="sm" onClick={downloadErrors}>
                    <Download className="h-4 w-4" /> Download error report (CSV)
                  </Button>
                </div>
              )}
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={close}>Close</Button>
          <Button onClick={upload} disabled={!file || busy}>
            {busy ? "Uploading…" : (uploadError || result?.errors.length ? "Try again" : "Upload")}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Fallback when the backend didn't tag the error with a field (older deploys
// or unexpected exceptions). Scans the reason text for known column names.
function guessField(e: ImportError): string | null {
  const text = e.reason.toLowerCase();
  const candidates = [
    "phone", "aadhar", "class_name", "date", "status", "student_id",
    "marks", "max_marks", "email", "name", "annual_fee", "dob", "exam_type", "subject",
  ];
  for (const k of candidates) {
    if (text.includes(k.replace("_", " ")) || text.includes(k)) return k;
  }
  return null;
}
