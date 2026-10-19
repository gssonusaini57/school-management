import * as React from "react";
import { format, isValid, parse } from "date-fns";
import { Calendar as CalendarIcon } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Calendar } from "@/components/ui/calendar";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { cn } from "@/lib/utils";

interface DatePickerProps {
  value: string;
  onChange: (iso: string) => void;
  min?: string;
  max?: string;
  placeholder?: string;
  className?: string;
  disabled?: boolean;
  id?: string;
  /** The visible label's id: the trigger is then named by it plus the date it shows. */
  "aria-labelledby"?: string;
}

const ISO = "yyyy-MM-dd";
const DISPLAY = "dd/MM/yyyy";

function parseIso(iso?: string): Date | undefined {
  if (!iso) return undefined;
  const d = parse(iso, ISO, new Date());
  return isValid(d) ? d : undefined;
}

export function DatePicker({
  value,
  onChange,
  min,
  max,
  placeholder = "Pick a date",
  className,
  disabled,
  id,
  "aria-labelledby": labelledBy,
}: DatePickerProps) {
  const [open, setOpen] = React.useState(false);
  const valueId = React.useId();

  const date = parseIso(value);
  const minDate = parseIso(min);
  const maxDate = parseIso(max);

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          id={id}
          aria-labelledby={labelledBy ? `${labelledBy} ${valueId}` : undefined}
          type="button"
          variant="outline"
          disabled={disabled}
          className={cn(
            "w-full justify-start font-normal",
            !date && "text-muted-foreground",
            className
          )}
        >
          <CalendarIcon className="mr-2 h-4 w-4" />
          <span id={valueId}>{date ? format(date, DISPLAY) : placeholder}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0" align="start">
        <Calendar
          mode="single"
          selected={date}
          defaultMonth={date ?? maxDate ?? new Date()}
          startMonth={minDate}
          endMonth={maxDate}
          captionLayout="dropdown"
          disabled={[
            ...(minDate ? [{ before: minDate }] : []),
            ...(maxDate ? [{ after: maxDate }] : []),
          ]}
          onSelect={(d) => {
            if (d) {
              onChange(format(d, ISO));
              setOpen(false);
            }
          }}
        />
      </PopoverContent>
    </Popover>
  );
}
