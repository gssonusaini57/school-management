package `in`.kisschool.ui.screens.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyListScope
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.OpenInNew
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.outlined.BeachAccess
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.CheckCircle
import androidx.compose.material.icons.outlined.DeleteOutline
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import `in`.kisschool.data.api.dto.BatchSummaryItemDto
import `in`.kisschool.data.api.dto.ClassAttendanceRowDto
import `in`.kisschool.data.api.dto.ClassAttendanceSummaryDto
import `in`.kisschool.data.api.dto.ClassAttendanceTotalsDto
import `in`.kisschool.data.repo.ApprovalCounts
import `in`.kisschool.data.repo.Notice
import `in`.kisschool.ui.components.DashboardCard
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.screens.notices.PriorityDot
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisColors
import `in`.kisschool.ui.theme.KisIcons
import `in`.kisschool.ui.theme.KisModule
import `in`.kisschool.util.relativeAge
import java.time.Instant
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.time.format.TextStyle
import java.util.Locale

/** Where the dashboard's taps go (wired to navigation in AppNav / HomeScreen). */
@Immutable
class DashboardActions(
    val onOpenAttendanceFor: (className: String, iso: String) -> Unit,
    /** The marked / pending / holiday classes of [iso], on their own screen. */
    val onOpenClasses: (kind: ClassDayKind, iso: String) -> Unit,
    val onApprovals: () -> Unit,
    /** Results, on [className] when given. */
    val onResults: (className: String?) -> Unit,
    /** Marks entry, on [className] when given. */
    val onMarksEntry: (className: String?) -> Unit,
    /** Students, on [className] when given. */
    val onStudents: (className: String?) -> Unit,
    val onNotices: () -> Unit,
    /** The web portal's fees page, in the browser (fees aren't in the app). */
    val onOpenFees: () -> Unit,
    val onRetry: (DashCard) -> Unit,
    val onSelectPeriod: (AttendancePeriod) -> Unit,
    /** Open or close a class's month calendar in the class-wise card. */
    val onToggleClass: (className: String) -> Unit,
    val onPrevMonth: () -> Unit,
    val onNextMonth: () -> Unit,
)

private val CardPadding = Modifier.padding(horizontal = 16.dp)
private val HERO_DATE: DateTimeFormatter = DateTimeFormatter.ofPattern("EEEE, d MMM", Locale.ENGLISH)
private val DAY_MONTH: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM", Locale.ENGLISH)
private val DAY_MONTH_YEAR: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.ENGLISH)

/**
 * A card slot: the card itself, or, when the server is too old for the card's endpoint,
 * the one-line note that stands in for it.
 */
private fun LazyListScope.cardItem(
    key: String,
    title: String,
    load: Loadable<*>,
    content: @Composable () -> Unit,
) {
    item(key = key) {
        val note = load.unavailable
        if (note != null) UnavailableNote(title, note, CardPadding) else content()
    }
}

// ── The two dashboards ──────────────────────────────────────────────────

/**
 * The admin and super-admin dashboard, in order: today at school, approvals (super-admin)
 * or session & term (admin), class-wise attendance, marks progress, fees, students &
 * staff, notices.
 */
fun LazyListScope.adminDashboard(cards: DashboardCards, coverage: DashboardUiState, actions: DashboardActions) {
    cardItem("today-at-school", "Today at school", cards.todaySummary) {
        TodayAtSchoolCard(cards.todaySummary, cards.today, actions, CardPadding)
    }
    if (cards.access.isSuperAdmin) {
        cardItem("approvals", "Needs your approval", cards.approvals) {
            ApprovalsCard(cards.approvals, actions, CardPadding)
        }
    } else {
        cardItem("session-term", "Session & term", cards.term) {
            SessionTermCard(cards.term, actions, CardPadding)
        }
    }
    item(key = "class-attendance") { ClassAttendanceCard(cards, coverage, actions, CardPadding) }
    cardItem("marks-progress", "Marks progress", cards.marksProgress) {
        MarksProgressCard(cards.marksProgress, actions, CardPadding)
    }
    cardItem("fees", "Fees collected", cards.fees) {
        FeesCard(cards.fees, cards.today, actions, CardPadding)
    }
    cardItem("headcount", "Students & staff", cards.headcount) {
        HeadcountCard(cards.headcount, cards.todaySummary.data?.classes, actions, CardPadding)
    }
    cardItem("notices", "Notices", cards.notices) { NoticesCard(cards.notices, actions, CardPadding) }
}

/**
 * The teacher dashboard, in order: today in my classes, class-wise attendance, marks to
 * finish (Marks entry grant), results readiness (Results grant), session & my students,
 * notices. Never fees, staff or approvals.
 */
fun LazyListScope.teacherDashboard(cards: DashboardCards, coverage: DashboardUiState, actions: DashboardActions) {
    cardItem("my-classes-today", "Today · my classes", cards.todaySummary) {
        TeacherTodayCard(cards.todaySummary, cards.today, actions, CardPadding)
    }
    item(key = "class-attendance") { ClassAttendanceCard(cards, coverage, actions, CardPadding) }
    if (cards.access.canMarksEntry) {
        cardItem("marks-to-finish", "Marks to finish", cards.marksTodo) {
            MarksTodoCard(cards.marksTodo, actions, CardPadding)
        }
    }
    if (cards.access.canResults) {
        cardItem("results-readiness", "Results readiness", cards.readiness) {
            ReadinessCard(cards.readiness, actions, CardPadding)
        }
    }
    item(key = "session-students") {
        SessionStudentsCard(cards.term, cards.todaySummary, coverage.allowedClasses, actions, CardPadding)
    }
    cardItem("notices", "Notices", cards.notices) { NoticesCard(cards.notices, actions, CardPadding) }
}

// ── Today at school (admins) ────────────────────────────────────────────

private fun KisColors.dayKindColor(kind: ClassDayKind): Color = when (kind) {
    ClassDayKind.MARKED -> present
    ClassDayKind.PENDING -> leave
    ClassDayKind.HOLIDAY -> noStatus
}

@Composable
private fun TodayAtSchoolCard(
    load: Loadable<ClassAttendanceSummaryDto>,
    today: LocalDate,
    actions: DashboardActions,
    modifier: Modifier = Modifier,
) {
    DashboardCard(
        module = KisModule.Attendance,
        title = "Today at school",
        icon = KisIcons.TakeAttendance,
        subtitle = HERO_DATE.format(today),
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.TODAY) }) { s ->
            val iso = today.toString()
            val counts = s.classes.dayCounts()
            NotASchoolDayNote(today)
            val open: (ClassDayKind) -> Unit = { kind -> actions.onOpenClasses(kind, iso) }
            // Side by side when there is room for both rings and their legends, else stacked.
            BoxWithConstraints(Modifier.fillMaxWidth()) {
                if (maxWidth >= 520.dp) {
                    Row(horizontalArrangement = Arrangement.spacedBy(24.dp)) {
                        ClassesRing(counts, open, Modifier.weight(1f))
                        StudentsRing(s.totals, Modifier.weight(1f))
                    }
                } else {
                    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                        ClassesRing(counts, open)
                        StudentsRing(s.totals)
                    }
                }
            }
            KpiGrid(attendanceKpis(s.totals, KISTheme.colors) + classKpis(counts, KISTheme.colors, open))
        }
    }
}

/** Classes today: marked / pending / holiday. Each part, and its legend line, opens that list. */
@Composable
private fun ClassesRing(counts: ClassDayCounts, onOpen: (ClassDayKind) -> Unit, modifier: Modifier = Modifier) {
    val colors = KISTheme.colors
    val kinds = ClassDayKind.entries
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        RingChart(
            parts = kinds.map { ChartPart(counts.of(it), colors.dayKindColor(it)) },
            centerValue = "${counts.marked} / ${counts.total}",
            centerLabel = "marked",
            description = buildString {
                append("Classes today: ${counts.marked} of ${plural(counts.total, "class")} marked, ")
                append("${counts.pending} pending")
                if (counts.holiday > 0) append(", ${counts.holiday} on holiday")
                append(".")
            },
            onPartClick = { i -> kinds.getOrNull(i)?.let { k -> if (counts.of(k) > 0) onOpen(k) } },
        )
        Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f)) {
            LegendHeading("Classes")
            kinds.forEach { k ->
                val n = counts.of(k)
                // A holiday line only when some class is on holiday (as on the web).
                if (k != ClassDayKind.HOLIDAY || n > 0) {
                    LegendRow(
                        color = colors.dayKindColor(k),
                        label = k.label,
                        value = "$n",
                        description = if (n > 0) "${k.label}: ${plural(n, "class")}, opens the list" else "${k.label}: no classes",
                        onClick = if (n > 0) ({ onOpen(k) }) else null,
                    )
                }
            }
        }
    }
}

/** Students today: present / half day / leave / absent, with the attendance percentage in the hole. */
@Composable
private fun StudentsRing(t: ClassAttendanceTotalsDto, modifier: Modifier = Modifier) {
    val colors = KISTheme.colors
    val parts = listOf(
        Triple("Present", t.present, colors.present),
        Triple("Half day", t.halfDay, colors.halfDay),
        Triple("Leave", t.leave, colors.leave),
        Triple("Absent", t.absent, colors.absent),
    )
    val pct = t.percent
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        RingChart(
            parts = parts.map { ChartPart(it.second, it.third) },
            centerValue = pct?.let(::formatPercent) ?: "—",
            centerLabel = if (pct != null) "present" else "none yet",
            description = if (pct == null) {
                "Students today: no attendance marked yet."
            } else {
                "Students today: ${spokenPercent(pct)} present. ${t.present} present, ${t.halfDay} half day, " +
                    "${t.leave} on leave, ${t.absent} absent."
            },
        )
        Spacer(Modifier.width(16.dp))
        Column(Modifier.weight(1f)) {
            LegendHeading("Students")
            parts.forEach { (label, n, color) ->
                LegendRow(color = color, label = label, value = "$n", description = "$label: ${plural(n, "student")}")
            }
        }
    }
}

@Composable
private fun LegendHeading(text: String) {
    Text(
        text,
        style = MaterialTheme.typography.labelLarge,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
        modifier = Modifier.padding(start = 8.dp, bottom = 2.dp),
    )
}

/** Present %, Absent, Leave, Half day for [t]. */
private fun attendanceKpis(t: ClassAttendanceTotalsDto, colors: KisColors): List<Kpi> = listOf(
    Kpi(
        KisIcons.Present, colors.present, "Present", t.percent?.let(::formatPercent) ?: "—",
        description = t.percent?.let { "Present: ${spokenPercent(it)} of the students marked" }
            ?: "Present: no attendance marked yet",
    ),
    Kpi(KisIcons.Absent, colors.absent, "Absent", "${t.absent}", "Absent: ${plural(t.absent, "student")}"),
    Kpi(KisIcons.Leave, colors.leave, "Leave", "${t.leave}", "On leave: ${plural(t.leave, "student")}"),
    Kpi(KisIcons.HalfDay, colors.halfDay, "Half day", "${t.halfDay}", "Half day: ${plural(t.halfDay, "student")}"),
)

/** "Marked X / Y" and "Pending N", each opening its list of classes. */
private fun classKpis(counts: ClassDayCounts, colors: KisColors, onOpen: (ClassDayKind) -> Unit): List<Kpi> = listOf(
    Kpi(
        KisIcons.ClassesMarked, colors.present, "Marked", "${counts.marked} / ${counts.total}",
        description = "Marked: ${counts.marked} of ${plural(counts.total, "class")}" +
            if (counts.marked > 0) ", opens the list" else "",
        onClick = if (counts.marked > 0) ({ onOpen(ClassDayKind.MARKED) }) else null,
    ),
    Kpi(
        KisIcons.NotMarked, colors.leave, "Pending", "${counts.pending}",
        description = if (counts.pending > 0) "Pending: ${plural(counts.pending, "class")}, opens the list" else "Pending: no classes",
        onClick = if (counts.pending > 0) ({ onOpen(ClassDayKind.PENDING) }) else null,
    ),
)

// ── Today · my classes (teachers) ───────────────────────────────────────

@OptIn(ExperimentalLayoutApi::class)
@Composable
private fun TeacherTodayCard(
    load: Loadable<ClassAttendanceSummaryDto>,
    today: LocalDate,
    actions: DashboardActions,
    modifier: Modifier = Modifier,
) {
    DashboardCard(
        module = KisModule.Attendance,
        title = "Today · my classes",
        icon = KisIcons.TakeAttendance,
        subtitle = HERO_DATE.format(today),
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.TODAY) }) { s ->
            if (s.classes.isEmpty()) {
                MutedText("No classes assigned yet.")
            } else {
                val iso = today.toString()
                NotASchoolDayNote(today)
                FlowRow(
                    Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    s.classes.forEach { row ->
                        ClassDayChip(row.className, row.dayKind()) { actions.onOpenAttendanceFor(row.className, iso) }
                    }
                }
                KpiGrid(attendanceKpis(s.totals, KISTheme.colors))
            }
        }
    }
}

/** A class's state today as a chip: icon and words, never colour alone. Opens that day's register. */
@Composable
private fun ClassDayChip(className: String, kind: ClassDayKind, onClick: () -> Unit) {
    val colors = KISTheme.colors
    val tint = colors.dayKindColor(kind)
    val (icon, text) = when (kind) {
        ClassDayKind.MARKED -> Icons.Outlined.CheckCircle to "Marked"
        ClassDayKind.PENDING -> KisIcons.NotMarked to "Not marked"
        ClassDayKind.HOLIDAY -> Icons.Outlined.BeachAccess to "Holiday"
    }
    val opens = if (kind == ClassDayKind.PENDING) "Opens take attendance." else "Opens the day's register."
    val shape = RoundedCornerShape(10.dp)
    Row(
        Modifier
            .heightIn(min = 48.dp)
            .clip(shape)
            .background(tint.copy(alpha = 0.14f))
            .border(1.dp, tint.copy(alpha = 0.6f), shape)
            .clickable(role = Role.Button, onClick = onClick)
            .clearAndSetSemantics { contentDescription = "$className: ${text.lowercase()}. $opens" }
            .padding(horizontal = 12.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(8.dp))
        Column {
            Text(
                className,
                style = MaterialTheme.typography.labelLarge,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Text(text, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

// ── Class-wise attendance (both) ────────────────────────────────────────

/** "19 Oct", "13–19 Oct", "29 Sep – 5 Oct". */
private fun dateRangeText(from: LocalDate, to: LocalDate): String = when {
    from == to -> DAY_MONTH.format(to)
    from.month == to.month && from.year == to.year -> "${from.dayOfMonth}–${DAY_MONTH.format(to)}"
    else -> "${DAY_MONTH.format(from)} – ${DAY_MONTH.format(to)}"
}

@Composable
private fun ClassAttendanceCard(
    cards: DashboardCards,
    coverage: DashboardUiState,
    actions: DashboardActions,
    modifier: Modifier = Modifier,
) {
    val colors = KISTheme.colors
    val period = cards.period
    val load = cards.barsSummary
    val (from, to) = period.range(cards.today)
    DashboardCard(
        module = KisModule.Attendance,
        title = "Class-wise attendance",
        icon = KisIcons.PastAttendance,
        subtitle = "${period.label} · ${dateRangeText(from, to)}",
        modifier = modifier,
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            AttendancePeriod.entries.forEach { p -> PeriodChip(p, selected = p == period) { actions.onSelectPeriod(p) } }
        }
        ColorKey(
            listOf(
                colors.present to "90% and up",
                colors.leave to "75–89%",
                colors.absent to "Under 75%",
                colors.noStatus to "Not marked",
            )
        )
        val unavailable = load.unavailable
        if (unavailable != null) {
            // An older server has no class summary: no bars, but every class still opens its month.
            MutedText(unavailable)
            ClassRows(
                rows = coverage.allowedClasses.map { ClassAttendanceRowDto(className = it) },
                showBars = false, multiDay = false, coverage = coverage, actions = actions,
            )
        } else {
            CardContent(load, onRetry = {
                actions.onRetry(if (period == AttendancePeriod.TODAY) DashCard.TODAY else DashCard.PERIOD)
            }) { s ->
                if (s.classes.isEmpty()) {
                    MutedText("No classes assigned yet.")
                } else {
                    MutedText("Tap a class to see its month.")
                    ClassRows(
                        rows = s.classes, showBars = true, multiDay = period != AttendancePeriod.TODAY,
                        coverage = coverage, actions = actions,
                    )
                }
            }
        }
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun PeriodChip(p: AttendancePeriod, selected: Boolean, onClick: () -> Unit) {
    FilterChip(selected = selected, onClick = onClick, label = { Text(p.label) })
}

@Composable
private fun ClassRows(
    rows: List<ClassAttendanceRowDto>,
    showBars: Boolean,
    multiDay: Boolean,
    coverage: DashboardUiState,
    actions: DashboardActions,
) {
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        rows.forEach { row ->
            val expanded = coverage.selectedClass == row.className
            ClassBarRow(row, showBars, multiDay, expanded) { actions.onToggleClass(row.className) }
            if (expanded) ExpandedMonth(row.className, coverage, actions)
        }
    }
}

/** What a class's bar says beside it, and what TalkBack reads for the row. */
private fun barTexts(row: ClassAttendanceRowDto, showBars: Boolean, multiDay: Boolean): Pair<String, String> {
    val pct = row.percent
    return when {
        !showBars -> "" to "${row.className}."
        pct != null -> {
            val over = if (multiDay) " over ${plural(row.markedDays, "day")}" else ""
            "${formatPercent(pct)} · ${row.present}/${row.records}" to
                "${row.className}: ${spokenPercent(pct)}, ${row.present} of ${row.records} present$over."
        }
        row.markedDays > 0 -> "Saved with no students" to "${row.className}: saved with no students."
        row.holidayDays > 0 -> "Holiday" to "${row.className}: holiday."
        else -> "Not marked" to "${row.className}: not marked."
    }
}

@Composable
private fun ClassBarRow(
    row: ClassAttendanceRowDto,
    showBars: Boolean,
    multiDay: Boolean,
    expanded: Boolean,
    onToggle: () -> Unit,
) {
    val colors = KISTheme.colors
    val accent = colors.module(KisModule.Attendance)
    val (label, spoken) = barTexts(row, showBars, multiDay)
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(if (expanded) accent.container else Color.Transparent)
            .clickable(
                role = Role.Button,
                onClickLabel = if (expanded) "hide the month" else "show the month",
                onClick = onToggle,
            )
            .clearAndSetSemantics {
                contentDescription = spoken
                stateDescription = if (expanded) "Month shown" else "Month hidden"
            }
            .heightIn(min = 48.dp)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                row.className,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f),
            )
            if (label.isNotEmpty()) {
                Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Icon(
                if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 4.dp).size(20.dp),
            )
        }
        if (showBars) PercentBar(row.percent, colors.attendanceBand(row.percent))
    }
}

/** The class's month calendar (the coverage calendar): tap a day to open that day's register. */
@Composable
private fun ExpandedMonth(cls: String, coverage: DashboardUiState, actions: DashboardActions) {
    Column(
        Modifier
            .fillMaxWidth()
            .padding(top = 4.dp, bottom = 8.dp),
        verticalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        if (coverage.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
        MonthCalendar(
            month = coverage.month,
            markedDates = coverage.markedDates,
            holidays = coverage.holidays,
            today = LocalDate.now(),
            onPrevMonth = actions.onPrevMonth,
            onNextMonth = actions.onNextMonth,
            onDayClick = { iso -> actions.onOpenAttendanceFor(cls, iso) },
            // Until the month arrives every day would read "missed": hold it back a little.
            modifier = Modifier.alpha(if (coverage.loading) 0.5f else 1f),
        )
        ErrorBanner(coverage.error)
    }
}

// ── Approvals (super-admin) ─────────────────────────────────────────────

@Composable
private fun ApprovalsCard(load: Loadable<ApprovalCounts>, actions: DashboardActions, modifier: Modifier = Modifier) {
    val colors = KISTheme.colors
    DashboardCard(
        module = KisModule.Approvals,
        title = "Needs your approval",
        icon = KisIcons.PendingApprovals,
        subtitle = load.data?.let { if (it.total > 0) plural(it.total, "request") + " waiting" else null },
        onClick = actions.onApprovals,
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.APPROVALS) }) { a ->
            if (a.total == 0 && a.error == null) {
                MutedText("Nothing is waiting for you.")
            } else {
                fun count(n: Int?) = n?.toString() ?: "—"
                fun spoken(what: String, n: Int?) = if (n == null) "$what: couldn't load" else "$what: $n waiting"
                KpiGrid(
                    listOf(
                        Kpi(KisIcons.Students, colors.module(KisModule.Students).fg, "Student edits", count(a.studentEdits), spoken("Student edits", a.studentEdits)),
                        Kpi(KisIcons.MarksEntry, colors.module(KisModule.Marks).fg, "Marks edits", count(a.marksEdits), spoken("Marks edits", a.marksEdits)),
                        Kpi(Icons.Outlined.DeleteOutline, colors.module(KisModule.Approvals).fg, "Deletions", count(a.deletions), spoken("Deletions", a.deletions)),
                    ),
                    minTileWidth = 88.dp,
                )
            }
            a.error?.let { MutedText(it) }
        }
    }
}

// ── Session & term ──────────────────────────────────────────────────────

@Composable
private fun SessionTermCard(load: Loadable<TermInfo>, actions: DashboardActions, modifier: Modifier = Modifier) {
    DashboardCard(
        module = KisModule.Marks,
        title = "Session & term",
        icon = Icons.Outlined.CalendarMonth,
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.TERM) }) { t ->
            TermDetails(t, KISTheme.colors.module(KisModule.Marks).fg)
        }
    }
}

private fun daysLeftText(t: TermInfo): String = when {
    t.daysLeft > 1 -> "${t.daysLeft} days left in ${t.label}"
    t.daysLeft == 1L -> "1 day left in ${t.label}: tomorrow is its last day"
    t.daysLeft == 0L -> "Today is the last day of ${t.label}"
    else -> "${t.label} ended on ${DAY_MONTH_YEAR.format(t.end)}"
}

/** Session, term and its dates, how far through it we are (a [barColor] meter), and the days left. */
@Composable
private fun TermDetails(t: TermInfo, barColor: Color) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Row(verticalAlignment = Alignment.Bottom) {
            Text(
                "Session ${t.session}",
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                modifier = Modifier.weight(1f),
            )
            Text(t.label, style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurface)
        }
        Text(
            "${DAY_MONTH_YEAR.format(t.start)} – ${DAY_MONTH_YEAR.format(t.end)}",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        PercentBar(t.elapsed * 100.0, barColor)
        Text(daysLeftText(t), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurface)
        if (!t.sessionFromServer) {
            MutedText("The server has no current session, so this is the school year by today's date.")
        } else if (!t.datesFromServer) {
            MutedText("The session has no dates for this term, so the school calendar is used (Term 1 April–September, Term 2 October–March).")
        }
    }
}

// ── Marks progress (admins) ─────────────────────────────────────────────

@Composable
private fun MarksProgressCard(load: Loadable<MarksProgress>, actions: DashboardActions, modifier: Modifier = Modifier) {
    val colors = KISTheme.colors
    val p0 = load.data
    DashboardCard(
        module = KisModule.Marks,
        title = if (p0 != null) "Marks progress · Term ${p0.term}" else "Marks progress",
        icon = KisIcons.MarksEntry,
        subtitle = p0?.let { "Session ${it.session} · tap a class for its results" },
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.MARKS_PROGRESS) }) { p ->
            KpiGrid(
                listOf(
                    Kpi(KisIcons.Submitted, colors.present, "Submitted", "${p.submitted}", "Submitted: ${plural(p.submitted, "exam")}"),
                    Kpi(KisIcons.Drafts, colors.leave, "Drafts", "${p.draft}", "In draft: ${plural(p.draft, "exam")}"),
                    Kpi(KisIcons.NotMarked, colors.noStatus, "Not started", "${p.missing}", "Not started: ${plural(p.missing, "exam")}"),
                ),
                minTileWidth = 88.dp,
            )
            if (p.classes.isEmpty()) {
                MutedText("No exams are set up for Term ${p.term} yet.")
            } else {
                ColorKey(listOf(colors.present to "Submitted", colors.leave to "Draft", colors.noStatus to "Not started"))
                Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    p.classes.forEach { c -> ClassMarksRow(c) { actions.onResults(c.className) } }
                }
            }
        }
    }
}

@Composable
private fun ClassMarksRow(c: ClassMarksProgress, onClick: () -> Unit) {
    val colors = KISTheme.colors
    val editRed = colors.module(KisModule.Approvals).fg
    val spoken = buildString {
        append("${c.className}: ")
        if (c.total == 0) append("no students to mark") else append("${c.submitted} submitted, ${c.draft} in draft, ${c.missing} not started")
        if (c.pendingEdits > 0) append(", ${plural(c.pendingEdits, "edit request")} waiting")
        append(".")
    }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable(role = Role.Button, onClickLabel = "open results", onClick = onClick)
            .clearAndSetSemantics { contentDescription = spoken }
            .heightIn(min = 48.dp)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                c.className,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            if (c.pendingEdits > 0) {
                Spacer(Modifier.width(8.dp))
                Dot(editRed)
                Text(
                    if (c.pendingEdits == 1) "Edit request" else "${c.pendingEdits} edit requests",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 4.dp),
                )
            }
            Spacer(Modifier.weight(1f))
            Text(
                if (c.total == 0) "No students to mark" else "${c.submitted}/${c.total} submitted",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        StackedBar(
            listOf(
                ChartPart(c.submitted, colors.present),
                ChartPart(c.draft, colors.leave),
                ChartPart(c.missing, colors.noStatus),
            )
        )
    }
}

// ── Fees (admins) ───────────────────────────────────────────────────────

@Composable
private fun FeesCard(load: Loadable<FeesSummary>, today: LocalDate, actions: DashboardActions, modifier: Modifier = Modifier) {
    val month = (load.data?.month?.month ?: today.month).getDisplayName(TextStyle.SHORT, Locale.ENGLISH)
    DashboardCard(
        module = KisModule.Fees,
        title = "Fees collected · $month",
        icon = KisIcons.FeesCollected,
        onClick = actions.onOpenFees,
        trailing = {
            Icon(
                Icons.AutoMirrored.Outlined.OpenInNew,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp),
            )
        },
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.FEES) }) { f ->
            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text(
                    formatRupees(f.total),
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = MaterialTheme.colorScheme.onSurface,
                )
                MutedText(if (f.count == 0) "No receipts yet this month" else "${plural(f.count, "receipt")} this month")
            }
            if (f.recent.isNotEmpty()) {
                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("Latest receipts", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    f.recent.forEach { r -> ReceiptRow(r) }
                }
            }
            MutedText("Opens the fees page of the web portal in your browser.")
        }
    }
}

@Composable
private fun ReceiptRow(r: FeeReceipt) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(
                r.studentName.ifBlank { "(No name)" },
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                listOfNotNull(r.className.ifBlank { null }, r.date?.let(DAY_MONTH::format), r.period.ifBlank { null })
                    .joinToString(" · "),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
        }
        Spacer(Modifier.width(8.dp))
        Text(
            formatRupees(r.amount),
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface,
        )
    }
}

// ── Students & staff (admins) ───────────────────────────────────────────

@Composable
private fun HeadcountCard(
    load: Loadable<Headcount>,
    classRows: List<ClassAttendanceRowDto>?,
    actions: DashboardActions,
    modifier: Modifier = Modifier,
) {
    val colors = KISTheme.colors
    DashboardCard(
        module = KisModule.Students,
        title = "Students & staff",
        icon = KisIcons.StudentsCount,
        onClick = { actions.onStudents(null) },
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.HEADCOUNT) }) { h ->
            KpiGrid(
                listOf(
                    Kpi(
                        KisIcons.StudentsCount, colors.module(KisModule.Students).fg, "Students", h.students?.toString() ?: "—",
                        h.students?.let { "Students: $it" } ?: "Students: couldn't load",
                    ),
                    Kpi(
                        KisIcons.Staff, colors.module(KisModule.Staff).fg, "Staff", h.staff?.toString() ?: "—",
                        h.staff?.let { "Staff: $it" } ?: "Staff: couldn't load",
                    ),
                ),
            )
            classRows?.sizeExtremes()?.let { (smallest, largest) ->
                Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(
                        "Largest class: ${largest.className} · ${plural(largest.size, "student")}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                    Text(
                        "Smallest class: ${smallest.className} · ${plural(smallest.size, "student")}",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurface,
                    )
                }
            }
            h.error?.let { MutedText(it) }
        }
    }
}

// ── Notices (both) ──────────────────────────────────────────────────────

@Composable
private fun NoticesCard(load: Loadable<List<Notice>>, actions: DashboardActions, modifier: Modifier = Modifier) {
    DashboardCard(
        module = KisModule.Notices,
        title = "Notices",
        icon = KisIcons.Notices,
        onClick = actions.onNotices,
        trailing = {
            Text("View all", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
        },
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.NOTICES) }) { list ->
            if (list.isEmpty()) {
                MutedText("No notices yet.")
            } else {
                val now = Instant.now()
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    list.forEach { n -> NoticeLine(n, now) }
                }
            }
        }
    }
}

@Composable
private fun NoticeLine(n: Notice, now: Instant) {
    Row(verticalAlignment = Alignment.Top) {
        PriorityDot(n.priority, Modifier.padding(top = 6.dp))
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(
                n.title.ifBlank { "(No title)" },
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            val meta = listOfNotNull(n.createdAt?.let { relativeAge(it, now) }, n.postedBy.ifBlank { null }).joinToString(" · ")
            if (meta.isNotEmpty()) MutedText(meta)
        }
    }
}

// ── Marks to finish (teachers) ──────────────────────────────────────────

private enum class TaskKind { READY, DRAFT, AWAITING }

@Composable
private fun MarksTodoCard(load: Loadable<MarksTodo>, actions: DashboardActions, modifier: Modifier = Modifier) {
    val colors = KISTheme.colors
    val m0 = load.data
    DashboardCard(
        module = KisModule.Marks,
        title = if (m0 != null) "Marks to finish · Term ${m0.term}" else "Marks to finish",
        icon = KisIcons.MarksEntry,
        subtitle = m0?.let { "Session ${it.session}" },
        onClick = { actions.onMarksEntry(null) },
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.MARKS_TODO) }) { m ->
            KpiGrid(
                listOf(
                    Kpi(KisIcons.ClassesMarked, colors.present, "Ready to submit", "${m.readyToSubmit.size}", "Ready to submit: ${plural(m.readyToSubmit.size, "exam")}"),
                    Kpi(KisIcons.Drafts, colors.leave, "Drafts", "${m.drafts.size}", "Drafts with marks still to enter: ${m.drafts.size}"),
                    Kpi(KisIcons.NotMarked, colors.noStatus, "Not started", "${m.notStartedCount}", "Not started: ${plural(m.notStartedCount, "exam")}"),
                ),
                minTileWidth = 88.dp,
            )
            if (m.allDone && m.awaitingApproval.isEmpty()) {
                MutedText(
                    if (m.submitted > 0) "Every Term ${m.term} exam is submitted." else "No exams are set up for Term ${m.term} yet."
                )
            }
            // The quickest wins first: ready to submit, then drafts, then the edit requests.
            val tasks = m.readyToSubmit.map { it to TaskKind.READY } +
                m.drafts.map { it to TaskKind.DRAFT } +
                m.awaitingApproval.map { it to TaskKind.AWAITING }
            if (tasks.isNotEmpty()) {
                Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    tasks.take(MAX_TASKS).forEach { (item, kind) ->
                        MarksTaskRow(item, kind) { actions.onMarksEntry(item.className) }
                    }
                }
                if (tasks.size > MAX_TASKS) MutedText("and ${tasks.size - MAX_TASKS} more in Marks entry")
            }
            if (m.notStarted.isNotEmpty()) {
                MutedText("Not started: " + m.notStarted.joinToString(" · ") { (cls, n) -> "$cls ${plural(n, "exam")}" })
            }
        }
    }
}

private const val MAX_TASKS = 5

@Composable
private fun MarksTaskRow(item: BatchSummaryItemDto, kind: TaskKind, onClick: () -> Unit) {
    val colors = KISTheme.colors
    val entered = "${item.entered}/${item.classSize} entered"
    val (icon: ImageVector, tint: Color, state: String) = when (kind) {
        TaskKind.READY -> Triple(KisIcons.ClassesMarked, colors.present, "Ready to submit · $entered")
        TaskKind.DRAFT -> Triple(KisIcons.Drafts, colors.leave, "Draft · $entered")
        TaskKind.AWAITING -> Triple(KisIcons.PendingApprovals, colors.module(KisModule.Approvals).fg, "Edit request waiting for approval")
    }
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable(role = Role.Button, onClickLabel = "open marks entry", onClick = onClick)
            .clearAndSetSemantics {
                contentDescription = "${item.className}, ${item.subject}, ${item.examType}: $state."
            }
            .heightIn(min = 48.dp)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(20.dp))
        Spacer(Modifier.width(10.dp))
        Column(Modifier.weight(1f)) {
            Text(
                "${item.className} · ${item.subject}",
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                "${item.examType} · $state",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
            )
        }
    }
}

// ── Results readiness (teachers) ────────────────────────────────────────

@Composable
private fun ReadinessCard(load: Loadable<ResultsReadiness>, actions: DashboardActions, modifier: Modifier = Modifier) {
    val r0 = load.data
    DashboardCard(
        module = KisModule.Results,
        title = if (r0 != null) "Results readiness · Term ${r0.term}" else "Results readiness",
        icon = KisIcons.Results,
        subtitle = r0?.let { "Session ${it.session}" },
        modifier = modifier,
    ) {
        CardContent(load, onRetry = { actions.onRetry(DashCard.READINESS) }) { r ->
            if (r.classes.isEmpty()) {
                MutedText("No classes assigned yet.")
            } else {
                Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    r.classes.forEach { c -> ReadinessRow(c) { actions.onResults(c.className) } }
                }
            }
        }
    }
}

@Composable
private fun ReadinessRow(c: ClassReadiness, onClick: () -> Unit) {
    val colors = KISTheme.colors
    val (icon, tint, state) = when {
        c.error != null -> Triple(KisIcons.About, colors.noStatus, c.error)
        c.complete -> Triple(Icons.Outlined.CheckCircle, colors.present, "Complete")
        c.hasDrafts -> Triple(KisIcons.Drafts, colors.leave, "Has drafts")
        c.ranked == 0 -> Triple(KisIcons.NotMarked, colors.noStatus, "No marks yet")
        else -> Triple(KisIcons.NotMarked, colors.noStatus, "In progress")
    }
    val ranked = when {
        c.error != null -> ""
        c.ranksKnown -> "${c.ranked} / ${c.classSize} ranked"
        else -> "${c.ranked} / ${c.classSize} with marks"
    }
    Column(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable(role = Role.Button, onClickLabel = "open results", onClick = onClick)
            .clearAndSetSemantics {
                contentDescription = listOf("${c.className}: $state", ranked).filter { it.isNotEmpty() }.joinToString(", ") + "."
            }
            .heightIn(min = 48.dp)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(20.dp))
            Spacer(Modifier.width(8.dp))
            Text(
                c.className,
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
                color = MaterialTheme.colorScheme.onSurface,
            )
            Spacer(Modifier.width(8.dp))
            Text(
                state,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f),
            )
            if (ranked.isNotEmpty()) {
                Text(ranked, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        if (c.error == null && c.classSize > 0) {
            PercentBar(c.ranked * 100.0 / c.classSize, colors.module(KisModule.Results).fg)
        }
    }
}

// ── Session & my students (teachers) ────────────────────────────────────

@Composable
private fun SessionStudentsCard(
    term: Loadable<TermInfo>,
    today: Loadable<ClassAttendanceSummaryDto>,
    classes: List<String>,
    actions: DashboardActions,
    modifier: Modifier = Modifier,
) {
    DashboardCard(
        module = KisModule.Students,
        title = "Session & my students",
        icon = KisIcons.Students,
        onClick = { actions.onStudents(null) },
        modifier = modifier,
    ) {
        CardContent(term, onRetry = { actions.onRetry(DashCard.TERM) }) { t ->
            TermDetails(t, KISTheme.colors.module(KisModule.Students).fg)
        }
        // Class sizes come with today's class summary; an older server lists the classes alone.
        val sizes = today.data?.classes?.associate { it.className to it.classSize }
        if (classes.isEmpty()) {
            MutedText("No classes assigned yet.")
        } else {
            Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                Text("My classes", style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                classes.forEach { c -> ClassSizeRow(c, sizes?.get(c)) { actions.onStudents(c) } }
            }
        }
    }
}

@Composable
private fun ClassSizeRow(className: String, size: Int?, onClick: () -> Unit) {
    val count = size?.let { plural(it, "student") }
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .clickable(role = Role.Button, onClickLabel = "open students", onClick = onClick)
            .clearAndSetSemantics { contentDescription = listOfNotNull(className, count).joinToString(": ") + "." }
            .heightIn(min = 48.dp)
            .padding(horizontal = 8.dp, vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            KisIcons.StudentsCount,
            contentDescription = null,
            tint = KISTheme.colors.module(KisModule.Students).fg,
            modifier = Modifier.size(20.dp),
        )
        Spacer(Modifier.width(10.dp))
        Text(
            className,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface,
            modifier = Modifier.weight(1f),
        )
        if (count != null) {
            Text(count, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

// ── Small pieces ────────────────────────────────────────────────────────

/**
 * On a day off in the working week (Sunday at KIS, see [WORKING_WEEK]) no class is expected
 * to mark attendance, so the "pending" classes are said to be expected.
 */
@Composable
private fun NotASchoolDayNote(today: LocalDate) {
    if (today.dayOfWeek in WORKING_WEEK.workingDays) return
    val day = today.dayOfWeek.getDisplayName(TextStyle.FULL, Locale.ENGLISH)
    MutedText("$day isn't a working day, so classes without attendance are expected today.")
}

@Composable
private fun MutedText(text: String) {
    Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}
