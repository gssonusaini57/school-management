import { useEffect, useMemo, useRef, type MutableRefObject, type RefObject } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate, useSearchParams } from "react-router-dom";
import { Doughnut } from "react-chartjs-2";
import { Chart as ChartJS, ArcElement, Tooltip, type ChartOptions } from "chart.js";
import { CalendarOff, ChevronLeft, ChevronRight, CircleCheck, Clock, type LucideIcon } from "lucide-react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { api, apiError } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ClassAttendanceRow, ClassAttendanceSummary } from "@/types/api";

ChartJS.register(ArcElement, Tooltip);

/** Today's per-class summary. The dashboard's SSE hook invalidates this key whenever
 *  attendance is saved, cleared or imported. */
export const CLASS_ATTENDANCE_KEY = ["attendance", "class-summary", "today"] as const;

/** Where a class stands today: attendance saved, not saved yet, or a holiday. */
type Coverage = "marked" | "pending" | "holiday";
const COVERAGES: readonly Coverage[] = ["marked", "pending", "holiday"];

/** The open list lives in the URL, so the browser's Back also returns to the chart. */
const VIEW_PARAM = "attendance";

/** A translation key with its English default. */
type Msg = { key: string; en: string };

/** Each state keeps its colour whatever its share (the KIS status colours), and is
 *  always shown with an icon and a label, never by colour alone. */
const STATES: Record<
  Coverage,
  { token: string; swatch: string; icon: LucideIcon; label: Msg; list: Msg; empty: Msg }
> = {
  marked: {
    token: "--color-success",
    swatch: "bg-success",
    icon: CircleCheck,
    label: { key: "portal.dashboard.classAttendance.marked", en: "Marked" },
    list: { key: "portal.dashboard.classAttendance.listMarked", en: "Marked classes" },
    empty: { key: "portal.dashboard.classAttendance.emptyMarked", en: "No class has marked attendance yet today." },
  },
  pending: {
    token: "--color-sangat-red",
    swatch: "bg-sangat-red",
    icon: Clock,
    label: { key: "portal.dashboard.classAttendance.pending", en: "Pending" },
    list: { key: "portal.dashboard.classAttendance.listPending", en: "Pending classes" },
    empty: { key: "portal.dashboard.classAttendance.emptyPending", en: "No class is pending today." },
  },
  holiday: {
    token: "--color-neutral-400",
    swatch: "bg-neutral-400",
    icon: CalendarOff,
    label: { key: "portal.dashboard.classAttendance.holiday", en: "Holiday" },
    list: { key: "portal.dashboard.classAttendance.listHoliday", en: "Classes on holiday" },
    empty: { key: "portal.dashboard.classAttendance.emptyHoliday", en: "No class is on holiday today." },
  },
};

function coverageOf(row: ClassAttendanceRow): Coverage {
  // A day is saved either as attendance or as a holiday, never both.
  if (row.marked_days > 0) return "marked";
  return row.holiday_days > 0 ? "holiday" : "pending";
}

/** A design token's value, for the chart canvas (which can't read CSS). */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/**
 * Today's attendance by class for admins and the super-admin: a doughnut of the
 * classes that have marked attendance, those still pending and those on holiday.
 * Clicking a part of it (or its row beside it) lists those classes; Back returns
 * to the chart.
 */
export function ClassAttendanceCard() {
  const { t, i18n } = useTranslation();
  const [searchParams, setSearchParams] = useSearchParams();
  const location = useLocation();
  const navigate = useNavigate();
  const param = searchParams.get(VIEW_PARAM);
  const view = COVERAGES.find((c) => c === param) ?? null;

  const q = useQuery({
    queryKey: CLASS_ATTENDANCE_KEY,
    // No dates: the server's today, so the card never asks for a day the server
    // hasn't reached yet. Refetched on focus so a tab left open overnight moves on.
    queryFn: () => api.get<ClassAttendanceSummary>("/attendance/class-summary").then((r) => r.data),
    refetchOnWindowFocus: true,
  });

  const groups = useMemo(() => {
    const g: Record<Coverage, ClassAttendanceRow[]> = { marked: [], pending: [], holiday: [] };
    for (const row of q.data?.classes ?? []) g[coverageOf(row)].push(row);
    return g;
  }, [q.data]);
  const total = q.data?.classes.length ?? 0;

  const open = (c: Coverage) =>
    setSearchParams(
      (prev) => {
        const next = new URLSearchParams(prev);
        next.set(VIEW_PARAM, c);
        return next;
      },
      { state: { fromAttendanceChart: true } },
    );
  const back = () => {
    // Opened from the chart: step back through history, so this button and the
    // browser's Back do the same thing. Opened from a link: drop the list from the URL.
    if ((location.state as { fromAttendanceChart?: boolean } | null)?.fromAttendanceChart) {
      navigate(-1);
    } else {
      setSearchParams(
        (prev) => {
          const next = new URLSearchParams(prev);
          next.delete(VIEW_PARAM);
          return next;
        },
        { replace: true },
      );
    }
  };

  // Focus follows the view (never on the first render): the list heading when a list
  // opens, and the row that opened it on the way back.
  const headingRef = useRef<HTMLHeadingElement>(null);
  const rowRefs = useRef<Partial<Record<Coverage, HTMLButtonElement | null>>>({});
  const shownView = useRef(view);
  useEffect(() => {
    const prev = shownView.current;
    shownView.current = view;
    if (prev === view) return;
    if (view) headingRef.current?.focus();
    else if (prev) rowRefs.current[prev]?.focus();
  }, [view]);

  return (
    <Card lang={i18n.language}>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-2 space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="font-display text-deep-indigo">
            {t("portal.dashboard.classAttendance.title", "Class attendance today")}
          </CardTitle>
          <CardDescription>
            {t(
              "portal.dashboard.classAttendance.subtitle",
              "Which classes have marked today's attendance, and which are still pending.",
            )}
          </CardDescription>
        </div>
        {q.data && <span className="text-sm font-medium text-muted-foreground">{formatDate(q.data.to)}</span>}
      </CardHeader>
      <CardContent>
        {q.isError && (
          <p role="alert" className="mb-3 text-sm text-destructive">
            {t("portal.dashboard.classAttendance.loadError", "Couldn't load class attendance: {{error}}", {
              error: apiError(q.error),
            })}
          </p>
        )}
        {q.isPending ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> {t("portal.common.loading", "Loading…")}
          </p>
        ) : !q.data ? null : total === 0 ? (
          <p className="text-sm text-muted-foreground">{t("portal.common.noData", "No data yet")}</p>
        ) : view ? (
          <ClassList view={view} rows={groups[view]} total={total} onBack={back} headingRef={headingRef} />
        ) : (
          <CoverageChart groups={groups} total={total} onOpen={open} rowRefs={rowRefs} />
        )}
      </CardContent>
    </Card>
  );
}

function CoverageChart({
  groups,
  total,
  onOpen,
  rowRefs,
}: {
  groups: Record<Coverage, ClassAttendanceRow[]>;
  total: number;
  onOpen: (c: Coverage) => void;
  rowRefs: MutableRefObject<Partial<Record<Coverage, HTMLButtonElement | null>>>;
}) {
  const { t, i18n } = useTranslation();
  const counts = COVERAGES.map((c) => groups[c].length);
  const [marked, pending, holiday] = counts;
  // The canvas can't read CSS, so it gets the token values; they never change at runtime.
  const colors = useMemo(() => COVERAGES.map((c) => token(STATES[c].token)), []);
  const surface = useMemo(() => token("--surface-page"), []);
  const font = { family: token(i18n.language === "pa" ? "--font-gurmukhi" : "--font-body") };
  // The surface-coloured gap between parts; a lone full ring has no neighbour to keep apart.
  const gap = counts.filter((n) => n > 0).length > 1 ? 2 : 0;
  // A holiday row only when some class is on holiday today.
  const rows = COVERAGES.filter((c) => c !== "holiday" || holiday > 0);

  const options: ChartOptions<"doughnut"> = {
    responsive: true,
    maintainAspectRatio: false,
    cutout: "68%",
    plugins: {
      legend: { display: false },
      tooltip: {
        titleFont: font,
        bodyFont: font,
        callbacks: {
          title: (items) => items[0]?.label ?? "",
          label: (item) =>
            t("portal.dashboard.classAttendance.classCount", "{{count}} classes", { count: item.parsed }),
        },
      },
    },
    onClick: (_event, elements) => {
      const i = elements[0]?.index;
      if (i !== undefined) onOpen(COVERAGES[i]);
    },
    onHover: (event, elements) => {
      const canvas = event.native?.target;
      if (canvas instanceof HTMLElement) canvas.style.cursor = elements.length ? "pointer" : "default";
    },
  };

  return (
    <div className="grid items-center gap-6 md:grid-cols-[220px_1fr]">
      <div className="relative mx-auto aspect-square w-full max-w-[220px]">
        <Doughnut
          role="img"
          aria-label={t(
            "portal.dashboard.classAttendance.chartLabel",
            "{{marked}} of {{total}} classes marked, {{pending}} pending, {{holiday}} on holiday",
            { marked, total, pending, holiday },
          )}
          data={{
            labels: COVERAGES.map((c) => t(STATES[c].label.key, STATES[c].label.en)),
            datasets: [
              {
                data: counts,
                backgroundColor: colors,
                hoverBackgroundColor: colors,
                borderColor: surface,
                hoverBorderColor: surface,
                borderWidth: gap,
                hoverOffset: 6,
              },
            ],
          }}
          options={options}
        />
        <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center text-center">
          <span className="font-display text-3xl font-bold text-deep-indigo tabular-nums">
            {marked}/{total}
          </span>
          <span className="max-w-[60%] text-xs text-muted-foreground">
            {t("portal.dashboard.classAttendance.centerCaption", "classes marked")}
          </span>
        </div>
      </div>

      <div className="space-y-2">
        {rows.map((c) => {
          const Icon = STATES[c].icon;
          return (
            <button
              key={c}
              type="button"
              ref={(el) => {
                rowRefs.current[c] = el;
              }}
              onClick={() => onOpen(c)}
              className="flex w-full items-center gap-3 rounded-lg border bg-background px-4 py-3 text-left transition-colors hover:bg-accent focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            >
              <span aria-hidden="true" className={cn("h-3 w-3 shrink-0 rounded-full", STATES[c].swatch)} />
              <Icon aria-hidden="true" className="h-4 w-4 shrink-0 text-muted-foreground" />
              <span className="flex-1 text-sm font-semibold text-foreground">{t(STATES[c].label.key, STATES[c].label.en)}</span>
              <span className="text-sm font-semibold text-foreground tabular-nums">
                {t("portal.dashboard.classAttendance.classCount", "{{count}} classes", { count: groups[c].length })}
              </span>
              <span className="inline-flex items-center gap-1 text-xs font-semibold text-primary">
                <span className="sr-only sm:not-sr-only">
                  {t("portal.dashboard.classAttendance.viewClasses", "View classes")}
                </span>
                <ChevronRight aria-hidden="true" className="h-4 w-4" />
              </span>
            </button>
          );
        })}
        <p className="pt-1 text-xs text-muted-foreground">
          {t("portal.dashboard.classAttendance.chartHint", "Click a part of the circle to see its classes.")}
        </p>
      </div>
    </div>
  );
}

function ClassList({
  view,
  rows,
  total,
  onBack,
  headingRef,
}: {
  view: Coverage;
  rows: ClassAttendanceRow[];
  total: number;
  onBack: () => void;
  headingRef: RefObject<HTMLHeadingElement>;
}) {
  const { t } = useTranslation();
  return (
    <div>
      <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
        <Button type="button" variant="outline" size="sm" onClick={onBack}>
          <ChevronLeft aria-hidden="true" /> {t("portal.dashboard.classAttendance.back", "Back")}
        </Button>
        <h2
          ref={headingRef}
          tabIndex={-1}
          className="flex items-center gap-2 text-heading-sm text-deep-indigo focus:outline-none"
        >
          <span aria-hidden="true" className={cn("h-3 w-3 shrink-0 rounded-full", STATES[view].swatch)} />
          {t(STATES[view].list.key, STATES[view].list.en)}
        </h2>
        <span className="text-sm text-muted-foreground tabular-nums">
          {t("portal.dashboard.classAttendance.listCount", "{{count}} of {{total}}", { count: rows.length, total })}
        </span>
      </div>

      {rows.length === 0 ? (
        <p className="mt-4 text-sm text-muted-foreground">{t(STATES[view].empty.key, STATES[view].empty.en)}</p>
      ) : (
        <ul className="mt-4 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {rows.map((row) => (
            <li key={row.class_name} className="rounded-lg border p-3">
              <div className="flex items-baseline justify-between gap-2">
                <span className="font-semibold text-foreground">{row.class_name}</span>
                {view === "marked" ? (
                  <span className="text-sm font-semibold text-foreground tabular-nums">
                    {row.percent == null
                      ? "—"
                      : t("portal.dashboard.classAttendance.percentPresent", "{{percent}}% present", {
                          percent: formatNumber(row.percent),
                        })}
                  </span>
                ) : (
                  <span className="text-sm text-muted-foreground tabular-nums">
                    {t("portal.dashboard.classAttendance.students", "{{count}} students", { count: row.class_size })}
                  </span>
                )}
              </div>
              {view === "marked" && (
                <p className="mt-1 text-xs text-muted-foreground tabular-nums">
                  {row.records === 0
                    ? t("portal.dashboard.classAttendance.noRecords", "Saved with no students")
                    : t(
                        "portal.dashboard.classAttendance.counts",
                        "Present {{present}} · Absent {{absent}} · Leave {{leave}} · Half day {{halfDay}}",
                        { present: row.present, absent: row.absent, leave: row.leave, halfDay: row.half_day },
                      )}
                </p>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
