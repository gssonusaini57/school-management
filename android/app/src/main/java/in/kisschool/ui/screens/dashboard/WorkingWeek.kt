package `in`.kisschool.ui.screens.dashboard

import java.time.DayOfWeek

/**
 * Which weekdays count as working days for "missed attendance" detection on the
 * coverage calendar. A past working day with no attendance record is flagged
 * "missed" (amber); non-working days render as off (grey). Holidays cannot be
 * auto-detected, so a holiday on a working day will appear as "missed" — the
 * calendar is informational, not punitive.
 *
 * Change [WORKING_WEEK] below to switch school policy in one place.
 */
enum class WorkingWeek(val workingDays: Set<DayOfWeek>) {
    MON_SAT(
        setOf(
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY, DayOfWeek.SATURDAY,
        )
    ),
    MON_FRI(
        setOf(
            DayOfWeek.MONDAY, DayOfWeek.TUESDAY, DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY, DayOfWeek.FRIDAY,
        )
    ),
    EVERY_DAY(DayOfWeek.values().toSet()),
    /** Never flag a day as "missed" (past unmarked working days render as off/grey). */
    NONE(emptySet()),
}

/** Active policy: KIS works Monday–Saturday (Sunday off). */
val WORKING_WEEK: WorkingWeek = WorkingWeek.MON_SAT
