import type { Student } from "@/types/api";

/**
 * Class-register order: by roll number (numerically when both are numbers), students
 * without one last, then by name. Marks Entry and the optional-subject checklist list
 * students in this order.
 */
export function compareByRoll(a: Pick<Student, "roll_no" | "name">, b: Pick<Student, "roll_no" | "name">): number {
  const ar = a.roll_no ?? "";
  const br = b.roll_no ?? "";
  if (ar !== "" || br !== "") {
    if (ar === "") return 1;
    if (br === "") return -1;
    const an = Number(ar);
    const bn = Number(br);
    if (!Number.isNaN(an) && !Number.isNaN(bn) && an !== bn) return an - bn;
    if (Number.isNaN(an) || Number.isNaN(bn)) {
      const c = ar.localeCompare(br);
      if (c !== 0) return c;
    }
  }
  return a.name.localeCompare(b.name);
}
