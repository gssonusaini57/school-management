import { useCallback, useMemo, useState, useSyncExternalStore } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type { TFunction } from "i18next";
import { Bar } from "react-chartjs-2";
import {
  Chart as ChartJS,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  type ChartData,
  type ChartOptions,
  type ScriptableScaleContext,
} from "chart.js";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Spinner } from "@/components/ui/spinner";
import { CLASS_ATTENDANCE_KEY } from "@/components/ClassAttendanceCard";
import { api, apiError } from "@/lib/api";
import { formatDate, formatNumber } from "@/lib/format";
import { cn } from "@/lib/utils";
import type { ClassAttendanceRow, ClassAttendanceSummary } from "@/types/api";

ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip);

/** The week and month summaries behind the chart, keyed by their dates. Today's is
 *  CLASS_ATTENDANCE_KEY, shared with the class attendance card so the dashboard asks
 *  for it once. The dashboard's SSE hook invalidates both when attendance changes. */
export const CLASS_CHART_KEY = ["attendance", "class-summary", "range"] as const;

/** Below this a class is red: the PSEB eligibility line, drawn dashed across the chart. */
const ELIGIBLE = 75;
/** From this a class is green. */
const GOOD = 90;

/** On a phone the bars run sideways, one row per class (px), above the percentage axis. */
const ROW_HEIGHT = 28;
const AXIS_HEIGHT = 40;

type Period = "today" | "week" | "month";
const PERIODS: readonly Period[] = ["today", "week", "month"];

/** A translation key with its English default. */
type Msg = { key: string; en: string };

const PERIOD_LABELS: Record<Period, Msg> = {
  today: { key: "portal.dashboard.classChart.today", en: "Today" },
  week: { key: "portal.dashboard.classChart.week", en: "This week" },
  month: { key: "portal.dashboard.classChart.month", en: "This month" },
};

/** Where a class's percentage falls. The colour repeats what the bar's length and the
 *  dashed 75 % line already show, so no band depends on colour alone. */
type Band = "good" | "watch" | "low" | "none";
const BANDS: readonly Band[] = ["good", "watch", "low", "none"];

const BAND_STYLES: Record<Band, { token: string; swatch: string; legend: Msg }> = {
  good: {
    token: "--color-success",
    swatch: "bg-success",
    legend: { key: "portal.dashboard.classChart.legendGood", en: "≥ 90 %" },
  },
  watch: {
    token: "--color-warning",
    swatch: "bg-warning",
    legend: { key: "portal.dashboard.classChart.legendWatch", en: "75–89 %" },
  },
  low: {
    token: "--color-sangat-red",
    swatch: "bg-sangat-red",
    legend: { key: "portal.dashboard.classChart.legendLow", en: "below 75 % (PSEB eligibility line)" },
  },
  none: {
    token: "--color-neutral-400",
    swatch: "bg-neutral-400",
    legend: { key: "portal.dashboard.classChart.notMarked", en: "Not marked" },
  },
};

function bandOf(percent: number | null): Band {
  if (percent == null) return "none";
  if (percent >= GOOD) return "good";
  return percent >= ELIGIBLE ? "watch" : "low";
}

/** A date as YYYY-MM-DD in the browser's own time zone (toISOString would give the UTC date). */
function isoDate(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
}

/** The dates a period asks for: none for today, so the server uses its own date;
 *  otherwise from Monday (or the 1st of the month) to today. */
function rangeOf(period: Period, now: Date): { from: string; to: string } | null {
  if (period === "today") return null;
  // getDay() is 0 on a Sunday, so a Sunday counts back six days to its Monday.
  const first = period === "month" ? 1 : now.getDate() - ((now.getDay() + 6) % 7);
  return { from: isoDate(new Date(now.getFullYear(), now.getMonth(), first)), to: isoDate(now) };
}

function rangeText(range: { from: string; to: string }, t: TFunction): string {
  if (range.from === range.to) return formatDate(range.to);
  return t("portal.dashboard.classChart.range", "{{from}} – {{to}}", {
    from: formatDate(range.from),
    to: formatDate(range.to),
  });
}

/** What a class with no attendance records shows in place of a percentage. */
function statusOf(row: ClassAttendanceRow, singleDay: boolean, t: TFunction): string {
  if (row.marked_days > 0) return t("portal.dashboard.classChart.savedEmpty", "Saved with no students");
  if (row.holiday_days > 0 && singleDay) return t("portal.dashboard.classChart.holiday", "Holiday");
  return t("portal.dashboard.classChart.notMarked", "Not marked");
}

/** "28.5 of 30": a half day counts as half present, as in the percentage. */
function presentOf(row: ClassAttendanceRow, t: TFunction): string {
  return t("portal.dashboard.classChart.presentOf", "{{present}} of {{records}}", {
    present: formatNumber(row.present + 0.5 * row.half_day),
    records: row.records,
  });
}

/** "3 days marked", plus the holidays when the period is longer than a day. */
function dayCounts(row: ClassAttendanceRow, singleDay: boolean, t: TFunction): string[] {
  const parts: string[] = [];
  if (row.marked_days > 0) {
    parts.push(t("portal.dashboard.classChart.daysMarked", "{{count}} days marked", { count: row.marked_days }));
  }
  if (row.holiday_days > 0 && !singleDay) {
    parts.push(t("portal.dashboard.classChart.holidays", "{{count}} holidays", { count: row.holiday_days }));
  }
  return parts;
}

/** The tooltip line: "92% · 28.5 of 30 · 1 day marked", or why there is no percentage. */
function summaryLine(row: ClassAttendanceRow, singleDay: boolean, t: TFunction): string {
  const head =
    row.percent == null ? [statusOf(row, singleDay, t)] : [`${formatNumber(row.percent)}%`, presentOf(row, t)];
  return [...head, ...dayCounts(row, singleDay, t)].join(" · ");
}

/** Whether a CSS media query matches, kept up to date as the window changes. */
function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = window.matchMedia(query);
      list.addEventListener("change", onChange);
      return () => list.removeEventListener("change", onChange);
    },
    [query],
  );
  return useSyncExternalStore(subscribe, () => window.matchMedia(query).matches);
}

/** A design token's value, for the chart canvas (which can't read CSS). */
function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/**
 * Attendance by class for today, this week or this month, for every role: admins and
 * the super-admin get every class, a teacher their own (the server decides). One bar
 * per class, coloured by band, with a dashed line at the PSEB 75 % mark.
 */
export function ClassAttendanceChart() {
  const { t, i18n } = useTranslation();
  const [period, setPeriod] = useState<Period>("today");
  // Worked out on every render, so a week or month left open past midnight moves on.
  const range = rangeOf(period, new Date());

  const q = useQuery({
    queryKey: range ? [...CLASS_CHART_KEY, range.from, range.to] : CLASS_ATTENDANCE_KEY,
    queryFn: () =>
      api
        .get<ClassAttendanceSummary>("/attendance/class-summary", { params: range ?? undefined })
        .then((r) => r.data),
    // A new period keeps the last chart on screen, dimmed, until its numbers arrive,
    // and every period change or return to the tab fetches fresh numbers.
    placeholderData: keepPreviousData,
    staleTime: 0,
    refetchOnWindowFocus: true,
  });

  const periodName = t(PERIOD_LABELS[period].key, PERIOD_LABELS[period].en);
  // The dates under the title: the server's, once this period's numbers are in.
  const settled = q.data && !q.isPlaceholderData ? q.data : undefined;
  const dates = settled ? { from: settled.from, to: settled.to } : range;
  const noClasses = settled?.classes.length === 0;

  return (
    <Card lang={i18n.language}>
      <CardHeader className="flex-row flex-wrap items-start justify-between gap-3 space-y-0">
        <div className="space-y-1.5">
          <CardTitle className="font-display text-deep-indigo">
            {t("portal.dashboard.classChart.title", "Class-wise attendance · {{period}}", { period: periodName })}
          </CardTitle>
          <CardDescription>
            {dates && <span className="font-semibold text-foreground">{rangeText(dates, t)} · </span>}
            {t(
              "portal.dashboard.classChart.subtitle",
              "Percentage of students present in each class; a half day counts as half.",
            )}
          </CardDescription>
        </div>
        {!noClasses && <PeriodToggle value={period} onChange={setPeriod} />}
      </CardHeader>
      <CardContent>
        {q.isError && (
          <p role="alert" className="mb-3 text-sm text-destructive">
            {t("portal.dashboard.classChart.loadError", "Couldn't load class-wise attendance: {{error}}", {
              error: apiError(q.error),
            })}
          </p>
        )}
        {q.isPending ? (
          <p className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> {t("portal.common.loading", "Loading…")}
          </p>
        ) : !q.data ? null : q.data.classes.length === 0 ? (
          <p className="text-sm text-muted-foreground">
            {t("portal.dashboard.classChart.noClasses", "No classes are assigned to your account yet.")}
          </p>
        ) : (
          <div
            aria-busy={q.isPlaceholderData}
            className={cn("transition-opacity", q.isPlaceholderData && "opacity-50")}
          >
            <AttendanceBars summary={q.data} />
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function PeriodToggle({ value, onChange }: { value: Period; onChange: (period: Period) => void }) {
  const { t } = useTranslation();
  return (
    <div
      role="group"
      aria-label={t("portal.dashboard.classChart.periodLabel", "Period")}
      className="inline-flex items-center rounded-full border border-input bg-background p-0.5"
    >
      {PERIODS.map((p) => (
        <button
          key={p}
          type="button"
          aria-pressed={value === p}
          onClick={() => onChange(p)}
          className={cn(
            "h-8 rounded-full px-3 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2",
            value === p ? "bg-primary text-primary-foreground" : "text-foreground hover:bg-accent",
          )}
        >
          {t(PERIOD_LABELS[p].key, PERIOD_LABELS[p].en)}
        </button>
      ))}
    </div>
  );
}

type BarScale = NonNullable<ChartOptions<"bar">["scales"]>[string];

function AttendanceBars({ summary }: { summary: ClassAttendanceSummary }) {
  const { t, i18n } = useTranslation();
  // Sideways bars on a phone, a row per class; upright bars from tablet width up.
  const horizontal = !useMediaQuery("(min-width: 768px)");
  const reduceMotion = useMediaQuery("(prefers-reduced-motion: reduce)");
  const rows = summary.classes;
  const singleDay = summary.from === summary.to;
  // The canvas can't read CSS, so it gets the token values; they never change at runtime.
  const ink = useMemo(
    () => ({
      band: Object.fromEntries(BANDS.map((b) => [b, token(BAND_STYLES[b].token)])) as Record<Band, string>,
      grid: token("--color-neutral-200"),
      baseline: token("--color-neutral-300"),
      line: token("--color-neutral-500"),
      text: token("--color-neutral-600"),
    }),
    [],
  );
  const family = token(i18n.language === "pa" ? "--font-gurmukhi" : "--font-body");

  const data = useMemo<ChartData<"bar", number[], string>>(
    () => ({
      labels: rows.map((r) => r.class_name),
      datasets: [
        {
          data: rows.map((r) => r.percent ?? 0),
          backgroundColor: rows.map((r) => ink.band[bandOf(r.percent)]),
          borderRadius: 4,
          maxBarThickness: 24,
          // A class with no records still gets a short neutral bar to point at.
          minBarLength: 4,
        },
      ],
    }),
    [rows, ink],
  );

  const options = useMemo<ChartOptions<"bar">>(() => {
    const onLine = (ctx: ScriptableScaleContext) => ctx.tick?.value === ELIGIBLE;
    const percentAxis: BarScale = {
      type: "linear",
      min: 0,
      max: 100,
      ticks: {
        stepSize: 25,
        color: ink.text,
        font: (ctx) => ({ family, size: 11, weight: onLine(ctx) ? "bold" : "normal" }),
        callback: (value) => `${value}%`,
      },
      grid: { color: (ctx) => (onLine(ctx) ? ink.line : ctx.tick?.value === 0 ? ink.baseline : ink.grid) },
      // No axis rule; `dash` styles this axis's grid lines, so only the 75 % line is dashed.
      border: { display: false, dash: (ctx) => (onLine(ctx) ? [4, 4] : []) },
    };
    const classAxis: BarScale = {
      type: "category",
      grid: { display: false },
      border: { display: false },
      ticks: { color: ink.text, font: { family, size: 11 }, autoSkip: false },
    };
    return {
      indexAxis: horizontal ? "y" : "x",
      responsive: true,
      maintainAspectRatio: false,
      animation: reduceMotion ? false : undefined,
      // Pointing anywhere in a class's slot, not only at its bar, shows its numbers.
      interaction: { mode: "index", intersect: false, axis: horizontal ? "y" : "x" },
      scales: horizontal ? { x: percentAxis, y: classAxis } : { x: classAxis, y: percentAxis },
      plugins: {
        legend: { display: false },
        tooltip: {
          displayColors: false,
          titleFont: { family, weight: "bold" },
          bodyFont: { family },
          callbacks: {
            title: (items) => items[0]?.label ?? "",
            label: (item) => summaryLine(rows[item.dataIndex], singleDay, t),
          },
        },
      },
    };
  }, [horizontal, reduceMotion, rows, singleDay, family, ink, t]);

  const rangeLabel = rangeText(summary, t);
  const { totals } = summary;
  const chartLabel =
    totals.classes_marked === 0
      ? t(
          "portal.dashboard.classChart.chartLabelEmpty",
          "Bar chart of attendance by class for {{range}}: no attendance marked yet.",
          { range: rangeLabel },
        )
      : t(
          "portal.dashboard.classChart.chartLabel",
          "Bar chart of attendance by class for {{range}}: {{marked}} of {{total}} classes marked, {{percent}}% present overall.",
          {
            range: rangeLabel,
            marked: totals.classes_marked,
            total: totals.classes_total,
            percent: formatNumber(totals.percent),
          },
        );

  return (
    <>
      <div
        className={cn("relative", !horizontal && "h-72")}
        style={horizontal ? { height: rows.length * ROW_HEIGHT + AXIS_HEIGHT } : undefined}
      >
        {/* Remounted when the bars change direction, so Chart.js rebuilds its axes. */}
        <Bar key={horizontal ? "rows" : "columns"} role="img" aria-label={chartLabel} data={data} options={options} />
      </div>

      <ul className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-muted-foreground">
        {BANDS.map((b) => (
          <li key={b} className="inline-flex items-center gap-1.5">
            <span aria-hidden="true" className={cn("h-2.5 w-2.5 shrink-0 rounded-sm", BAND_STYLES[b].swatch)} />
            {t(BAND_STYLES[b].legend.key, BAND_STYLES[b].legend.en)}
          </li>
        ))}
      </ul>

      {/* The chart's numbers for screen readers. */}
      <table className="sr-only">
        <caption>
          {t("portal.dashboard.classChart.tableCaption", "Attendance by class, {{range}}", { range: rangeLabel })}
        </caption>
        <thead>
          <tr>
            <th scope="col">{t("portal.dashboard.classChart.colClass", "Class")}</th>
            <th scope="col">{t("portal.dashboard.classChart.colPercent", "Present (%)")}</th>
            <th scope="col">{t("portal.dashboard.classChart.colPresent", "Present out of marked")}</th>
            <th scope="col">{t("portal.dashboard.classChart.colDays", "Days")}</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.class_name}>
              <th scope="row">{row.class_name}</th>
              <td>{row.percent == null ? statusOf(row, singleDay, t) : `${formatNumber(row.percent)}%`}</td>
              <td>{row.percent == null ? "—" : presentOf(row, t)}</td>
              <td>{dayCounts(row, singleDay, t).join(" · ") || "—"}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </>
  );
}
