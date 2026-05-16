/**
 * Indian-grouping currency: ₹ 1,00,000.00 (lakhs/crores), not ₹ 100,000.00.
 * Always rendered with a non-breaking space between the symbol and the number.
 */
export function formatINR(amount: number, options?: { fraction?: 0 | 2 }): string {
  const fraction = options?.fraction ?? 2;
  const formatted = new Intl.NumberFormat("en-IN", {
    minimumFractionDigits: fraction,
    maximumFractionDigits: fraction,
  }).format(amount);
  return `₹ ${formatted}`;
}

/**
 * Default date format used everywhere except PSEB documents:
 *   2026-05-08  →  "08 May 2026"
 *
 * PSEB-mandated format on admit cards / date sheets:
 *   2026-05-08  →  "08-05-2026"
 */
export function formatDate(iso: string, mode: "default" | "pseb" = "default"): string {
  const d = parseLooseDate(iso);
  if (!d) return iso;
  if (mode === "pseb") {
    return `${pad(d.getDate())}-${pad(d.getMonth() + 1)}-${d.getFullYear()}`;
  }
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  return `${pad(d.getDate())} ${months[d.getMonth()]} ${d.getFullYear()}`;
}

function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

function parseLooseDate(input: string): Date | null {
  if (!input) return null;
  // Accept "YYYY-MM-DD" or full ISO; treat date-only as local-time midnight to
  // avoid the Asia/Kolkata vs UTC edge case where Date("2026-05-08") parses to
  // the previous day's evening.
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(input);
  if (dateOnly) {
    const [, y, m, day] = dateOnly;
    return new Date(Number(y), Number(m) - 1, Number(day));
  }
  const d = new Date(input);
  return Number.isNaN(d.getTime()) ? null : d;
}
