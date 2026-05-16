import { api, apiError, getToken } from "./api";
import { toast } from "@/components/ui/toaster";

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
