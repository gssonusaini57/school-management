import axios from "axios";
import { queryOptions } from "@tanstack/react-query";
import { api, apiError, getToken } from "./api";
import i18n from "./i18n";
import { toast } from "@/components/ui/toaster";
import type { PdfRoster, PdfTemplate, RenderJob, ResultScope } from "@/types/api";

const baseURL = (import.meta.env.VITE_API_URL as string | undefined) ?? "/api";

/**
 * POST {payload} to /api/pdf/{kind}, save the response blob with `filename`.
 * Surfaces validation errors as a toast and rethrows so callers can handle UI state.
 */
export async function downloadPdf(kind: string, payload: unknown, filename: string): Promise<void> {
  try {
    const res = await api.post(`/pdf/${kind}`, payload, { responseType: "blob" });
    const url = URL.createObjectURL(res.data as Blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    toast(apiError(e), "error");
    throw e;
  }
}

/**
 * URL for a server-cached PDF blob, embedding the JWT as a query param so an
 * <a href download> works without the browser needing to send Bearer headers.
 * Mirrors the existing `fileUrl()` pattern for student documents.
 */
export function cachedPdfUrl(pdfId: number): string {
  const t = getToken();
  return `${baseURL}/pdf/cache/${pdfId}/inline?token=${encodeURIComponent(t)}`;
}

/** Trigger a browser download of a cached PDF by id. */
export function downloadCachedPdf(pdfId: number, filename: string): void {
  const a = document.createElement("a");
  a.href = cachedPdfUrl(pdfId);
  a.download = filename.endsWith(".pdf") ? filename : `${filename}.pdf`;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// ── Report-card render jobs + preview ────────────────────────────────

/** Characters per language in a report-card remark (REMARK_MAX in app/pdf/schemas.py). */
export const REMARK_MAX = 600;

/** True for a 4xx response: asking again won't change the answer. */
export function isClientError(e: unknown): boolean {
  const status = axios.isAxiosError(e) ? e.response?.status : undefined;
  return status != null && status >= 400 && status < 500;
}

/** A render job that is still queued or running. */
export function isRenderJobActive(job: Pick<RenderJob, "status"> | null | undefined): boolean {
  return job?.status === "queued" || job?.status === "running";
}

/**
 * GET /pdf/render-jobs/{id}. Shared so every component watching a job reads
 * the same cache entry (RenderJobProgress adds the polling interval).
 */
export function renderJobQuery(jobId: number) {
  return queryOptions({
    queryKey: ["pdf-render-job", jobId] as const,
    queryFn: () => api.get<RenderJob>(`/pdf/render-jobs/${jobId}`).then((r) => r.data),
    retry: (failures: number, e: Error) => !isClientError(e) && failures < 2,
  });
}

/** GET /pdf/templates/resolve: the report-card template for a class, session and scope, or null. */
export function templateResolveQuery(cls: string, session: string, scope: ResultScope) {
  return queryOptions({
    queryKey: ["pdf-template-resolve", cls, session, scope] as const,
    queryFn: () =>
      api
        .get<PdfTemplate | null>("/pdf/templates/resolve", { params: { class: cls, session, scope } })
        .then((r) => r.data ?? null),
    retry: (failures: number, e: Error) => !isClientError(e) && failures < 1,
  });
}

/** GET /pdf/templates/{id}/roster, shared by every view of one report-card template. */
export function templateRosterQuery(templateId: number) {
  return queryOptions({
    queryKey: ["pdf-roster", templateId] as const,
    queryFn: () => api.get<PdfRoster>(`/pdf/templates/${templateId}/roster`).then((r) => r.data),
    retry: (failures: number, e: Error) => !isClientError(e) && failures < 1,
  });
}

/** URL of the ZIP with every card a finished render job produced (JWT in the query, like cachedPdfUrl). */
export function renderJobZipUrl(jobId: number): string {
  const t = getToken();
  return `${baseURL}/pdf/render-jobs/${jobId}/zip/inline?token=${encodeURIComponent(t)}`;
}

/** Trigger a browser download of a finished render job's ZIP. The server names the file. */
export function downloadRenderJobZip(jobId: number): void {
  const a = document.createElement("a");
  a.href = renderJobZipUrl(jobId);
  a.setAttribute("download", "");
  document.body.appendChild(a);
  a.click();
  a.remove();
}

/** apiError() for a `responseType: "blob"` request, whose error body also arrives as a Blob. */
async function blobApiError(e: unknown): Promise<string> {
  if (axios.isAxiosError(e) && e.response?.data instanceof Blob) {
    try {
      e.response.data = JSON.parse(await e.response.data.text());
    } catch {
      // Not JSON: apiError falls back to the HTTP status message.
    }
  }
  return apiError(e);
}

/**
 * Render one report card without the cache (admin only) and show it in a new tab.
 * The preview endpoint needs the Bearer header, so it is fetched as a blob rather
 * than opened as a ?token= URL.
 */
export async function openReportCardPreview(templateId: number, studentId: number): Promise<void> {
  const waiting = i18n.t("portal.reportCards.previewLoading", "Preparing the preview…");
  // Open the tab now, while still inside the click, so pop-up blockers allow it;
  // it is pointed at the PDF once the render comes back.
  const win = window.open("", "_blank");
  if (win) {
    try {
      win.opener = null;
      win.document.title = waiting;
      if (win.document.body) win.document.body.textContent = waiting;
    } catch {
      // The blank tab is only a placeholder; not every browser lets us write to it.
    }
  }
  try {
    const res = await api.get<Blob>(`/pdf/templates/${templateId}/preview`, {
      params: { student_id: studentId, format: "pdf" },
      responseType: "blob",
      timeout: 2 * 60_000,
    });
    const url = URL.createObjectURL(new Blob([res.data], { type: "application/pdf" }));
    window.setTimeout(() => URL.revokeObjectURL(url), 60_000);
    if (win && !win.closed) {
      win.location.href = url;
      return;
    }
    // Pop-ups blocked: save the file instead of losing the render.
    const a = document.createElement("a");
    a.href = url;
    a.download = `report-card-preview-${studentId}.pdf`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast(i18n.t("portal.reportCards.previewDownloaded", "Pop-ups are blocked, so the preview was downloaded instead."), "warning");
  } catch (e) {
    if (win && !win.closed) win.close();
    toast(await blobApiError(e), "error");
  }
}
