import { useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import type { Meta } from "@/types/api";

/** Same values the backend serves today (app/services/results.py, app/constants.py);
 *  used only until GET /meta has loaded, so a slow network never blanks a picker. */
export const FALLBACK_META: Meta = {
  classes: ["Nursery", "L.K.G", "U.K.G", "1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th", "11th", "12th"],
  grade_bands: [
    { grade: "A1", min_pct: 91 }, { grade: "A2", min_pct: 81 }, { grade: "B1", min_pct: 71 },
    { grade: "B2", min_pct: 61 }, { grade: "C1", min_pct: 51 }, { grade: "C2", min_pct: 41 }, { grade: "D", min_pct: 0 },
  ],
  grade_legend: [
    { grade: "A1", range: "91–100" }, { grade: "A2", range: "81–90" }, { grade: "B1", range: "71–80" },
    { grade: "B2", range: "61–70" }, { grade: "C1", range: "51–60" }, { grade: "C2", range: "41–50" },
    { grade: "D", range: "below 41" },
  ],
  grade_letters: ["A1", "A2", "B1", "B2", "C1", "C2", "D"],
  houses: ["Ravidas", "Tagore", "Bhagat Singh", "Nanak"],
  promotion_values: ["Promoted", "Conditional", "Detained"],
  pass_pct: 33,
  conditional_max_fails: 2,
  scopes: ["term1", "term2", "annual"],
  menu_keys: [],
};

/** Reference lists from the backend (classes, grade letters, houses, …). */
export function useMeta(): Meta {
  const { data } = useQuery<Meta>({
    queryKey: ["meta"],
    queryFn: () => api.get("/meta").then((r) => r.data),
    staleTime: 60 * 60_000,
  });
  return data ?? FALLBACK_META;
}
