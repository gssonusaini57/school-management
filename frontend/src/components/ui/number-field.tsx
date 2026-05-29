import * as React from "react";
import { Input } from "./input";
import { cn } from "@/lib/utils";

/**
 * Number input that doesn't trap users into editing a leading zero.
 *
 * The classic bug: a `<Input type="number">` whose state defaults to `0`
 * shows "0" and the parent's `onChange={(e) => setState(Number(e.target.value) || 0)}`
 * resets to `0` the instant the user clears the field, so they can't ever
 * start fresh. Teachers hit this on Max Marks (showed 100, hit 3 to type
 * "30", got "1003"...).
 *
 * Contract:
 *   - State holds a `string` ("" when empty), not a number.
 *   - The parent decides what to do with "" at submit time (`Number(v) || 0`).
 *   - `max` is enforced visually (red border) and `clampOnBlur` snaps the value
 *     back into range when the field loses focus.
 *
 * Spinner arrows are hidden globally by the base Input component (see input.tsx).
 */
export interface NumberFieldProps
  extends Omit<React.InputHTMLAttributes<HTMLInputElement>, "value" | "onChange" | "type"> {
  value: string;
  onChange: (next: string) => void;
  max?: number;
  min?: number;
  /** Snap to min/max on blur. Off by default — parents that just need
   *  visual feedback (and validate at submit) usually prefer it off. */
  clampOnBlur?: boolean;
  /** Visual indicator when the parsed number exceeds `max`. */
  invalid?: boolean;
}

const digitsAndDot = (raw: string): string => {
  // Strip everything except digits + a single leading minus + a single dot.
  // Lets users paste "₹1,200.50" → "1200.50". Doesn't try to do full locale parsing.
  let out = "";
  let dotSeen = false;
  for (let i = 0; i < raw.length; i++) {
    const ch = raw[i];
    if (ch >= "0" && ch <= "9") out += ch;
    else if (ch === "." && !dotSeen) { out += ch; dotSeen = true; }
    else if (ch === "-" && i === 0) out += ch;
  }
  return out;
};

export const NumberField = React.forwardRef<HTMLInputElement, NumberFieldProps>(
  ({ value, onChange, max, min, clampOnBlur, invalid, className, onBlur, ...rest }, ref) => {
    const parsed = value === "" ? null : Number(value);
    const overMax = parsed != null && max != null && parsed > max;
    const underMin = parsed != null && min != null && parsed < min;
    // We hard-reject keystrokes that exceed `max`/`min`, so this only
    // triggers when the value was somehow set out-of-range externally OR
    // when the parent passes `invalid` explicitly.
    const isInvalid = invalid || overMax || underMin;

    return (
      <Input
        ref={ref}
        type="number"
        inputMode="decimal"
        value={value}
        max={max}
        min={min}
        onChange={(e) => {
          const next = digitsAndDot(e.target.value);
          if (next === "") {
            onChange(next);
            return;
          }
          const n = Number(next);
          // Reject the keystroke if the resulting number would exceed bounds.
          // Allow intermediate forms like "" / "." / "0." (NaN-on-parse) so
          // the user can still type a decimal. The controlled <input> snaps
          // back to the previous value on the next render.
          if (Number.isFinite(n)) {
            if (max != null && n > max) return;
            if (min != null && n < min) return;
          }
          onChange(next);
        }}
        onBlur={(e) => {
          if (clampOnBlur && parsed != null) {
            let next = parsed;
            if (max != null && next > max) next = max;
            if (min != null && next < min) next = min;
            if (next !== parsed) onChange(String(next));
          }
          onBlur?.(e);
        }}
        className={cn(isInvalid && "border-destructive focus-visible:ring-destructive", className)}
        {...rest}
      />
    );
  }
);
NumberField.displayName = "NumberField";
