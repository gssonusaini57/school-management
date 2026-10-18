import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useSessions } from "@/lib/session";

/** Picker over the configured academic sessions; the current one is labelled. */
export function SessionSelect({ value, onChange }: { value: string; onChange: (session: string) => void }) {
  const { data = [] } = useSessions();
  // Keep a value that isn't (yet) in the list selectable, e.g. while loading.
  const names = data.map((s) => s.session);
  const options = value && !names.includes(value) ? [value, ...names] : names;
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger><SelectValue placeholder="Select session" /></SelectTrigger>
      <SelectContent>
        {options.map((name) => {
          const row = data.find((s) => s.session === name);
          return (
            <SelectItem key={name} value={name}>
              {name}{row?.is_current ? " (current)" : ""}
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}
