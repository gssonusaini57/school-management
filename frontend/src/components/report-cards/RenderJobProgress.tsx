import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Ban, CheckCircle2, ChevronDown, ChevronUp, FileArchive, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { useAuth } from "@/lib/auth";
import { downloadRenderJobZip, isClientError, isRenderJobActive, renderJobQuery } from "@/lib/pdf";
import { cn } from "@/lib/utils";
import type { PdfRoster, PdfStudentRosterRow, RenderJob } from "@/types/api";

const POLL_MS = 1500;
/** Up to this many errors are listed straight away; more go behind a toggle. */
const ERRORS_LISTED_OPEN = 3;
/** The runner finishes the card it is on before honouring a cancel. */
const AFTER_CANCEL_REFRESH_MS = 4000;

/**
 * Live progress of one background render run (POST /pdf/templates/{id}/render-jobs).
 * Polls every 1.5 s while the job is queued or running, then stops; calls
 * `onFinished` once when the job ends (done, failed or cancelled).
 * `roster` is the class roster as it stands now, loaded at `rosterUpdatedAt`: a run's
 * card whose student no longer shows that card as current has gone out of date.
 */
export function RenderJobProgress({
  jobId,
  onFinished,
  roster,
  rosterUpdatedAt = 0,
}: {
  jobId: number;
  onFinished?: (job: RenderJob) => void;
  roster?: PdfStudentRosterRow[];
  rosterUpdatedAt?: number;
}) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const { user, isAdmin } = useAuth();
  const [showErrors, setShowErrors] = useState(false);

  const jobQ = useQuery({
    ...renderJobQuery(jobId),
    refetchInterval: (query) => {
      // A 4xx won't change by asking again (the run, or its template, was deleted): stop,
      // even when an earlier poll left a running job in the cache.
      if (isClientError(query.state.error)) return false;
      const job = query.state.data;
      if (job) return isRenderJobActive(job) ? POLL_MS : false;
      return POLL_MS; // nothing loaded yet: keep trying through a restart
    },
  });
  const job = jobQ.data;
  // Loaded before, but the server no longer answers for it: what is shown is out of date.
  const lost = !!job && isClientError(jobQ.error);

  const onFinishedRef = useRef(onFinished);
  useEffect(() => {
    onFinishedRef.current = onFinished;
  });
  const reportedFor = useRef<number | null>(null);
  // When this panel saw the run end. A roster loaded before then predates the run's last
  // cards, so it can't tell which of them are current (onFinished reloads it).
  const endedAt = useRef<number | null>(null);
  useEffect(() => {
    if (!job || isRenderJobActive(job) || reportedFor.current === job.id) return;
    reportedFor.current = job.id;
    endedAt.current = Date.now();
    onFinishedRef.current?.(job);
  }, [job]);

  const cancel = useMutation({
    mutationFn: () => api.post<RenderJob>(`/pdf/render-jobs/${jobId}/cancel`).then((r) => r.data),
    onSuccess: (cancelled) => {
      qc.setQueryData(renderJobQuery(jobId).queryKey, cancelled);
      // Pick up the card that was in progress when the cancel landed.
      window.setTimeout(() => {
        qc.invalidateQueries({ queryKey: renderJobQuery(jobId).queryKey });
        qc.invalidateQueries({ queryKey: ["pdf-roster", cancelled.template_id] });
      }, AFTER_CANCEL_REFRESH_MS);
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  if (jobQ.isPending) {
    return (
      <div className="flex items-center gap-2 rounded-md border bg-card p-3 text-sm text-muted-foreground">
        <Spinner /> {t("portal.reportCards.jobLoading", "Loading the generation run…")}
      </div>
    );
  }
  if (!job) {
    return (
      <div role="alert" className="rounded-md border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive">
        {t("portal.reportCards.jobLoadError", "Couldn't load this generation run.")} {apiError(jobQ.error)}
      </div>
    );
  }

  // Names come from the roster the caller already loaded; no extra request.
  const cachedRoster = qc.getQueryData<PdfRoster | PdfStudentRosterRow[]>(["pdf-roster", job.template_id]);
  const rosterRows = roster ?? (Array.isArray(cachedRoster) ? cachedRoster : cachedRoster?.students ?? []);
  const studentLabel = (id: number): string => {
    const s = rosterRows.find((r) => r.id === id);
    if (!s) return t("portal.reportCards.studentNumber", "Student #{{id}}", { id });
    return s.roll_no ? `${s.roll_no} · ${s.name}` : s.name;
  };

  const active = isRenderJobActive(job) && !lost;
  const pct = job.total > 0 ? Math.min(100, Math.round((job.done_count / job.total) * 100)) : 0;
  const errors = job.results.filter((r) => r.status === "error");
  const ready = job.results.filter((r) => r.status !== "error" && r.pdf_id != null).length;
  // Cards this run made that the roster now shows as "Needs update" (a remark or a mark
  // changed since): the ZIP leaves them out, so it must not pass for the whole class.
  const rosterCurrent = !!roster && endedAt.current != null && rosterUpdatedAt > endedAt.current;
  const outdated =
    roster && rosterCurrent && !active
      ? job.results.filter((r) => {
          if (r.pdf_id == null) return false;
          const row = roster.find((s) => s.id === r.student_id);
          return !!row && row.cached_pdf_id !== r.pdf_id;
        }).length
      : 0;
  const madeCount = job.results.filter((r) => r.pdf_id != null).length;
  const canDownload = !active && !lost && madeCount > outdated;
  const downloadZip = () => {
    if (
      outdated > 0 &&
      !window.confirm(
        t(
          "portal.reportCards.zipOutdatedConfirm",
          "{{count}} cards from this run are out of date and are left out of the ZIP. Download the other cards anyway?",
          { count: outdated },
        ),
      )
    ) {
      return;
    }
    downloadRenderJobZip(job.id);
  };
  // The server lets the person who started the run, or an admin, cancel it.
  const canCancel = active && (isAdmin || job.requested_by === user?.name);
  const errorsOpen = errors.length <= ERRORS_LISTED_OPEN || showErrors;

  const statusText: Record<RenderJob["status"], string> = {
    queued: t("portal.reportCards.jobQueued", "Waiting to start…"),
    running: t("portal.reportCards.jobRunning", "Generating report cards…"),
    done: t("portal.reportCards.jobDone", "Finished"),
    failed: t("portal.reportCards.jobFailed", "Stopped with an error"),
    cancelled: t("portal.reportCards.jobCancelled", "Cancelled"),
  };
  const barClass: Record<RenderJob["status"], string> = {
    queued: "bg-primary/40",
    running: "bg-primary",
    done: errors.length ? "bg-warning" : "bg-success",
    failed: "bg-destructive",
    cancelled: "bg-muted-foreground/50",
  };

  return (
    <div className="space-y-2 rounded-md border bg-card p-3 text-sm">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-medium" aria-live="polite">
          {active ? (
            <Spinner />
          ) : job.status === "done" && !errors.length ? (
            <CheckCircle2 className="h-4 w-4 text-success" />
          ) : job.status === "cancelled" ? (
            <Ban className="h-4 w-4 text-muted-foreground" />
          ) : (
            <TriangleAlert className="h-4 w-4 text-warning" />
          )}
          <span>{lost ? t("portal.reportCards.jobLoadError", "Couldn't load this generation run.") : statusText[job.status]}</span>
          <span className="font-normal tabular-nums text-muted-foreground">
            {t("portal.reportCards.progress", "{{done}} of {{total}}", { done: job.done_count, total: job.total })}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {canCancel && (
            <Button size="sm" variant="outline" onClick={() => cancel.mutate()} disabled={cancel.isPending}>
              {cancel.isPending ? <Spinner /> : <Ban />} {t("portal.reportCards.cancel", "Cancel")}
            </Button>
          )}
          {canDownload && (
            <Button size="sm" variant={outdated > 0 ? "outline" : "default"} onClick={downloadZip}>
              <FileArchive /> {t("portal.reportCards.downloadZip", "Download ZIP")}
            </Button>
          )}
        </div>
      </div>

      <div
        role="progressbar"
        aria-label={t("portal.reportCards.progressLabel", "Report cards generated")}
        aria-valuemin={0}
        aria-valuemax={job.total}
        aria-valuenow={job.done_count}
        className="h-2 w-full overflow-hidden rounded-full bg-muted"
      >
        <div className={cn("h-full rounded-full transition-[width] duration-500", barClass[job.status])} style={{ width: `${pct}%` }} />
      </div>

      <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
        <span>{t("portal.reportCards.readyCount", "{{count}} ready", { count: ready })}</span>
        {errors.length > 0 && (
          <span className="text-destructive">{t("portal.reportCards.errorCount", "Errors: {{count}}", { count: errors.length })}</span>
        )}
        {job.requested_by && <span>{t("portal.reportCards.startedBy", "Started by {{name}}", { name: job.requested_by })}</span>}
      </div>

      {lost && (
        <p role="alert" className="text-sm text-destructive">{apiError(jobQ.error)}</p>
      )}
      {outdated > 0 && (
        <p role="status" className="flex items-start gap-1.5 text-xs text-amber-800">
          <TriangleAlert className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden />
          {t(
            "portal.reportCards.zipOutdated",
            "{{count}} cards from this run changed afterwards (they show “Needs update”), so the ZIP leaves them out. Generate them again to include them.",
            { count: outdated },
          )}
        </p>
      )}
      {job.status === "failed" && job.error && (
        <p role="alert" className="text-sm text-destructive">{job.error}</p>
      )}

      {errors.length > 0 && (
        <div>
          {errors.length > ERRORS_LISTED_OPEN && (
            <Button
              variant="link"
              size="sm"
              className="h-auto px-0 text-xs"
              aria-expanded={showErrors}
              onClick={() => setShowErrors((v) => !v)}
            >
              {showErrors ? <ChevronUp /> : <ChevronDown />}
              {showErrors
                ? t("portal.reportCards.hideErrors", "Hide errors")
                : t("portal.reportCards.showErrors", "Show errors ({{count}})", { count: errors.length })}
            </Button>
          )}
          {errorsOpen && (
            <ul className="mt-1 space-y-1 text-xs">
              {errors.map((r) => (
                <li key={r.student_id}>
                  <span className="font-medium">{studentLabel(r.student_id)}</span>
                  <span className="text-destructive"> — {r.error || t("portal.reportCards.unknownError", "Unknown error")}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
