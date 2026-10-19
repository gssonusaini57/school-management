import { useEffect, useId, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Save, TriangleAlert } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Spinner } from "@/components/ui/spinner";
import { toast } from "@/components/ui/toaster";
import { api, apiError } from "@/lib/api";
import { compareByRoll } from "@/lib/roster";
import { confirmLeave, useUnsavedChanges } from "@/lib/unsaved";
import { cn } from "@/lib/utils";
import type { ClassSubject, ClassSubjectDetail, Student, SubjectEnrollments } from "@/types/api";

/** A set of student ids as a stable string ("3,7,12"), to compare two sets. */
const idsKey = (ids: Iterable<number>): string =>
  Array.from(ids)
    .sort((a, b) => a - b)
    .join(",");

/** A save: the ids sent, and the ticks they were taken from (to tell whether they changed meanwhile). */
interface SaveVars {
  ids: number[];
  from: Set<number>;
}

/**
 * Who takes a subject, on its Class Subjects page (super-admin). Most subjects are taken by
 * the whole class. An optional one (11th/12th Mathematics as an additional subject) is taken
 * only by the students ticked here: only they get marks, results and a line on the report
 * card for it, and it never affects anyone's promotion.
 */
export function OptionalSubjectCard({ subject }: { subject: ClassSubjectDetail }) {
  const { t } = useTranslation();
  const qc = useQueryClient();
  const titleId = useId();
  const optional = !!subject.is_optional;
  const serverIds = subject.enrolled_student_ids ?? [];
  const serverKey = idsKey(serverIds);

  // The class's students (not archived), as Marks Entry lists them.
  const studentsQ = useQuery<Student[]>({
    queryKey: ["students", subject.class_name],
    queryFn: () =>
      api.get("/students", { params: { class: subject.class_name, page_size: 500 } }).then((r) => r.data.items),
    enabled: optional,
  });
  const roster = useMemo(() => (studentsQ.data ?? []).slice().sort(compareByRoll), [studentsQ.data]);

  // The ticks follow the saved set (another super-admin's save arrives over SSE) while they
  // have no edits; ticks with edits keep them. While the subject isn't optional they are hidden
  // and always match the saved set.
  const [picked, setPicked] = useState<Set<number>>(() => new Set(serverIds));
  const followed = useRef(serverKey);
  useEffect(() => {
    const prev = followed.current;
    followed.current = serverKey;
    setPicked((p) => {
      const key = idsKey(p);
      const follow = !optional || key === prev;
      return follow && key !== serverKey ? new Set(serverIds) : p;
    });
  }, [serverKey, optional]);

  const dirty = optional && idsKey(picked) !== serverKey;
  // Leaving the page or reloading it asks first while the ticks aren't saved.
  useUnsavedChanges(dirty);

  /** The PATCH and PUT answers carry no components: fold their fields into the cached detail. */
  const patchDetail = (fields: Partial<ClassSubject>) =>
    qc.setQueryData<ClassSubjectDetail>(["class-subjects", subject.id], (old) => (old ? { ...old, ...fields } : old));
  /** Who takes the subject decides results, report-card rosters and who Marks Entry lists. */
  const refreshDependents = () => {
    qc.invalidateQueries({ queryKey: ["class-subjects"] });
    qc.invalidateQueries({ queryKey: ["results"] });
    qc.invalidateQueries({ queryKey: ["pdf-roster"] });
  };

  const setOptional = useMutation({
    mutationFn: (next: boolean) =>
      api.patch<ClassSubject>(`/class-subjects/${subject.id}`, { is_optional: next }).then((r) => r.data),
    onSuccess: (saved) => {
      const ids = saved.enrolled_student_ids ?? [];
      patchDetail({ is_optional: !!saved.is_optional, enrolled_student_ids: ids, updated_at: saved.updated_at });
      setPicked(new Set(ids));
      toast(
        saved.is_optional
          ? t("portal.classSubjects.optionalOn", "{{subject}} is now an optional subject. Tick the students who take it, then save.", {
              subject: subject.subject_name,
            })
          : t("portal.classSubjects.optionalOff", "{{subject}} is taken by the whole class again.", {
              subject: subject.subject_name,
            }),
        "success",
      );
      refreshDependents();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const save = useMutation({
    mutationFn: ({ ids }: SaveVars) =>
      api
        .put<SubjectEnrollments>(`/class-subjects/${subject.id}/enrollments`, { student_ids: ids })
        .then((r) => r.data),
    onSuccess: (saved, vars) => {
      patchDetail({ is_optional: saved.is_optional, enrolled_student_ids: saved.student_ids });
      // Start again from what was stored, unless the ticks changed while saving.
      setPicked((p) => (p === vars.from ? new Set(saved.student_ids) : p));
      toast(
        t("portal.classSubjects.takersSaved", "Saved. {{count}} students take {{subject}}.", {
          count: saved.student_ids.length,
          subject: subject.subject_name,
        }),
        "success",
      );
      refreshDependents();
    },
    onError: (e) => toast(apiError(e), "error"),
  });

  const busy = save.isPending || setOptional.isPending;
  const takingCount = roster.filter((s) => picked.has(s.id)).length;

  const onOptionalChange = (next: boolean) => {
    if (next === optional || busy) return;
    // Turning it off hides the ticks, so unsaved ones are asked about first.
    if (!next && !confirmLeave()) return;
    setOptional.mutate(next);
  };

  const toggle = (id: number, on: boolean) =>
    setPicked((p) => {
      const next = new Set(p);
      if (on) next.add(id);
      else next.delete(id);
      return next;
    });

  const onSave = () => {
    // Only students on the class's roster: one who left the class or was archived since
    // this page loaded would be refused by the server.
    const ids = roster.filter((s) => picked.has(s.id)).map((s) => s.id);
    save.mutate({ ids, from: picked });
  };

  // A server older than optional subjects (a half-done deploy) doesn't send the field.
  if (subject.is_optional === undefined) return null;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle id={titleId} className="text-deep-indigo">
          {t("portal.classSubjects.whoTakesTitle", "Who takes this subject")}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <label className="flex cursor-pointer items-start gap-3">
          <Checkbox
            className="mt-0.5"
            checked={optional}
            disabled={busy}
            onCheckedChange={(v) => onOptionalChange(v === true)}
          />
          <span className="space-y-0.5">
            <span className="block text-sm font-medium">{t("portal.classSubjects.optionalLabel", "Optional subject")}</span>
            <span className="block text-sm text-muted-foreground">
              {t(
                "portal.classSubjects.optionalHint",
                "Only the students ticked below get marks and results for this subject. It never affects promotion.",
              )}
            </span>
          </span>
        </label>

        {!optional ? (
          <p className="text-sm text-muted-foreground">
            {t(
              "portal.classSubjects.wholeClass",
              "The whole class takes {{subject}}. Tick “Optional subject” if only some students take it, such as Mathematics as an additional subject in 11th and 12th.",
              { subject: subject.subject_name },
            )}
          </p>
        ) : studentsQ.isPending ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Spinner /> {t("portal.common.loading", "Loading…")}
          </div>
        ) : studentsQ.isError ? (
          <div role="alert" className="flex flex-wrap items-center gap-2 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            <TriangleAlert className="h-4 w-4 shrink-0" aria-hidden />
            <span>
              {t("portal.classSubjects.studentsLoadError", "Couldn't load the students of {{cls}}.", { cls: subject.class_name })}{" "}
              {apiError(studentsQ.error)}
            </span>
            <Button variant="outline" size="sm" className="ml-auto" onClick={() => void studentsQ.refetch()}>
              {t("portal.common.tryAgain", "Try again")}
            </Button>
          </div>
        ) : !roster.length ? (
          <p className="text-sm text-muted-foreground">
            {t("portal.classSubjects.noStudents", "No students in {{cls}} yet.", { cls: subject.class_name })}
          </p>
        ) : (
          <div className="space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="text-sm font-medium" aria-live="polite">
                {t("portal.classSubjects.takersCount", "{{count}} of {{total}} students take this subject", {
                  count: takingCount,
                  total: roster.length,
                })}
              </p>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={busy || takingCount === roster.length}
                  onClick={() => setPicked(new Set(roster.map((s) => s.id)))}
                >
                  {t("portal.classSubjects.selectAll", "Select all")}
                </Button>
                <Button variant="outline" size="sm" disabled={busy || picked.size === 0} onClick={() => setPicked(new Set())}>
                  {t("portal.classSubjects.clearAll", "Clear")}
                </Button>
                <Button size="sm" disabled={!dirty || busy} onClick={onSave}>
                  <Save className="h-4 w-4" />{" "}
                  {save.isPending ? t("portal.common.saving", "Saving…") : t("portal.actions.saveChanges", "Save changes")}
                </Button>
              </div>
            </div>
            <ul aria-labelledby={titleId} className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {roster.map((s) => {
                const on = picked.has(s.id);
                return (
                  <li key={s.id}>
                    <label
                      className={cn(
                        "flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2 hover:bg-muted/40",
                        on && "border-primary/40 bg-primary/5",
                      )}
                    >
                      <Checkbox checked={on} disabled={busy} onCheckedChange={(v) => toggle(s.id, v === true)} />
                      <span className="w-8 shrink-0 text-right font-mono text-xs text-muted-foreground">{s.roll_no || "—"}</span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-medium">{s.name}</span>
                        {s.father && (
                          <span className="block truncate text-xs text-muted-foreground">
                            {t("portal.classSubjects.father", "Father: {{name}}", { name: s.father })}
                          </span>
                        )}
                      </span>
                    </label>
                  </li>
                );
              })}
            </ul>
            {dirty && (
              <p className="text-xs text-amber-700">
                {t("portal.classSubjects.takersUnsaved", "Changes to who takes this subject aren't saved yet.")}
              </p>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
