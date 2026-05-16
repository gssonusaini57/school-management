import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatDate(d: string | Date | null | undefined) {
  if (!d) return "—";
  return new Date(d).toLocaleDateString("en-IN", {
    day: "2-digit",
    month: "short",
    year: "numeric",
  });
}

export function formatCurrency(n: number | string | null | undefined) {
  const v = Number(n ?? 0);
  return "₹" + v.toLocaleString("en-IN");
}

export const CLASSES = [
  "Nursery", "L.K.G", "U.K.G",
  "1st", "2nd", "3rd", "4th", "5th", "6th",
  "7th", "8th", "9th", "10th", "11th", "12th",
];

export const COLORS = [
  "#6366f1", "#22c55e", "#f59e0b", "#ef4444", "#38bdf8",
  "#a78bfa", "#fb923c", "#34d399", "#f472b6", "#60a5fa",
  "#facc15", "#4ade80", "#f87171", "#818cf8", "#2dd4bf",
];

export const RELIGIONS = [
  "Hindu", "Muslim", "Sikh", "Christian", "Jain", "Buddhist", "Parsi", "Other",
];

// "  raj   KUMAR singh " → "Raj Kumar Singh"
export function toTitleCase(s: string): string {
  return (s ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase()
    .replace(/(^|\s|-|')(\p{L})/gu, (_, sep, c) => sep + c.toUpperCase());
}

// Strip everything that isn't a digit. Useful for phone / aadhaar inputs.
export function digitsOnly(s: string): string {
  return (s ?? "").replace(/\D+/g, "");
}

// ISO YYYY-MM-DD bounds for a `<input type="date">` student-DOB picker.
// Today as the latest (no future DOBs); 25 years back as the earliest (covers
// every nursery-to-12th student with margin for late admissions).
export function dobBounds(): { min: string; max: string } {
  const today = new Date();
  const earliest = new Date(today);
  earliest.setFullYear(today.getFullYear() - 25);
  return {
    min: earliest.toISOString().slice(0, 10),
    max: today.toISOString().slice(0, 10),
  };
}
