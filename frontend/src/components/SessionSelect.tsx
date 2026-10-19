import { useTranslation } from "react-i18next";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { useSessions } from "@/lib/session";

/** Picker over the configured academic sessions; the current one is labelled. `id` goes on the trigger, for <Label htmlFor>. */
export function SessionSelect({
  id,
  value,
  onChange,
  disabled,
}: {
  id?: string;
  value: string;
  onChange: (session: string) => void;
  disabled?: boolean;
}) {
  const { t } = useTranslation();
  const { data = [] } = useSessions();
  // Keep a value that isn't (yet) in the list selectable, e.g. while loading.
  const names = data.map((s) => s.session);
  const options = value && !names.includes(value) ? [value, ...names] : names;
  return (
    <Select value={value} onValueChange={onChange} disabled={disabled}>
      <SelectTrigger id={id}>
        <SelectValue placeholder={t("portal.common.selectSession", "Select session")} />
      </SelectTrigger>
      <SelectContent>
        {options.map((name) => {
          const row = data.find((s) => s.session === name);
          return (
            <SelectItem key={name} value={name}>
              {row?.is_current ? t("portal.templates.currentSession", "{{session}} (current)", { session: name }) : name}
            </SelectItem>
          );
        })}
      </SelectContent>
    </Select>
  );
}
