package `in`.kisschool.ui.screens.dashboard

import android.icu.text.NumberFormat
import androidx.compose.runtime.Immutable
import `in`.kisschool.data.CLASSES
import `in`.kisschool.data.api.dto.BatchSummaryItemDto
import `in`.kisschool.data.api.dto.ClassAttendanceRowDto
import `in`.kisschool.data.api.dto.ClassResultsDto
import `in`.kisschool.data.api.dto.FeePaymentDto
import `in`.kisschool.data.repo.SessionChoice
import `in`.kisschool.data.repo.SessionRepository
import `in`.kisschool.ui.screens.results.hasAnyMarks
import java.math.BigDecimal
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.YearMonth
import java.time.temporal.ChronoUnit
import java.util.Locale
import kotlin.math.abs
import kotlin.math.atan2
import kotlin.math.roundToLong

/*
 * The dashboard's rules, kept free of Compose and of the network so each one is stated
 * once: which classes count as marked / pending / holiday, which part of a ring a tap
 * lands on, which term today is in, and what a teacher still has to finish.
 */

// ── One card's data ─────────────────────────────────────────────────────

/**
 * A dashboard card's data and how its last load went. [data] is kept while a reload
 * runs (the card dims it) and when a reload fails ([error] then shows above it).
 * [unavailable] is set when the server is older than the card's endpoint: the card is
 * replaced by a one-line note and the rest of the dashboard carries on.
 */
@Immutable
data class Loadable<out T>(
    val loading: Boolean = false,
    val data: T? = null,
    val error: String? = null,
    val unavailable: String? = null,
)

/** Who is looking at the dashboard; decides which cards it has. */
@Immutable
data class DashboardAccess(
    /** "super_admin" | "admin" | "staff", or null until /auth/me has said. */
    val role: String? = null,
    /** The staff menu grants (admins always pass both). */
    val canMarksEntry: Boolean = false,
    val canResults: Boolean = false,
) {
    val isAdmin: Boolean get() = role == "admin" || role == "super_admin"
    val isSuperAdmin: Boolean get() = role == "super_admin"
}

// ── Classes today: marked / pending / holiday ──────────────────────────

/** Where a class stands on one day. [key] is the route segment of its list screen. */
enum class ClassDayKind(val key: String, val label: String) {
    MARKED("marked", "Marked"),
    PENDING("pending", "Pending"),
    HOLIDAY("holiday", "Holiday");

    companion object {
        fun of(key: String?): ClassDayKind = entries.firstOrNull { it.key == key } ?: PENDING
    }
}

/**
 * A class's state over a one-day summary. A day is saved either as attendance or as a
 * holiday, never both (the web's rule too): marked when attendance is saved, holiday when
 * only a holiday is, pending when there is neither.
 */
fun ClassAttendanceRowDto.dayKind(): ClassDayKind = when {
    markedDays > 0 -> ClassDayKind.MARKED
    holidayDays > 0 -> ClassDayKind.HOLIDAY
    else -> ClassDayKind.PENDING
}

@Immutable
data class ClassDayCounts(val marked: Int, val pending: Int, val holiday: Int) {
    val total: Int get() = marked + pending + holiday
    fun of(kind: ClassDayKind): Int = when (kind) {
        ClassDayKind.MARKED -> marked
        ClassDayKind.PENDING -> pending
        ClassDayKind.HOLIDAY -> holiday
    }
}

fun List<ClassAttendanceRowDto>.dayCounts(): ClassDayCounts = ClassDayCounts(
    marked = count { it.dayKind() == ClassDayKind.MARKED },
    pending = count { it.dayKind() == ClassDayKind.PENDING },
    holiday = count { it.dayKind() == ClassDayKind.HOLIDAY },
)

/** The period the class-wise attendance card covers. */
enum class AttendancePeriod(val label: String) {
    TODAY("Today"),
    WEEK("This week"),
    MONTH("This month");

    /** First and last day (inclusive): the week runs from Monday, the month from the 1st, both up to [today]. */
    fun range(today: LocalDate): Pair<LocalDate, LocalDate> = when (this) {
        TODAY -> today to today
        WEEK -> today.with(DayOfWeek.MONDAY) to today
        MONTH -> today.withDayOfMonth(1) to today
    }
}

// ── Ring geometry ───────────────────────────────────────────────────────

/**
 * The angle of the point ([dx], [dy]) from a ring's centre, in degrees clockwise from
 * 12 o'clock (screen axes: y grows downwards), in 0 until 360.
 */
fun clockAngle(dx: Float, dy: Float): Float {
    val deg = Math.toDegrees(atan2(dy.toDouble(), dx.toDouble())).toFloat() + 90f
    return ((deg % 360f) + 360f) % 360f
}

/**
 * Which part of a ring a tap at [angle] (see [clockAngle]) lands on. The parts are drawn
 * clockwise from 12 o'clock in [values] order, each over its share of the circle; a part
 * with no value takes no room. Null for an empty ring. A tap in the thin gap between two
 * parts counts for the part the gap closes.
 */
fun ringPartAt(angle: Float, values: List<Int>): Int? {
    val total = values.sumOf { it.coerceAtLeast(0) }
    if (total == 0) return null
    val a = ((angle % 360f) + 360f) % 360f
    var end = 0f
    var last: Int? = null
    values.forEachIndexed { i, v ->
        if (v <= 0) return@forEachIndexed
        end += v * 360f / total
        last = i
        if (a < end) return i
    }
    return last
}

// ── Session and term ────────────────────────────────────────────────────

/** The term today falls in, and its dates. */
@Immutable
data class TermInfo(
    /** e.g. "2026-27". */
    val session: String,
    /** 1 or 2. */
    val term: Int,
    val start: LocalDate,
    val end: LocalDate,
    val today: LocalDate,
    /** False when the server has no dates for this term and the school calendar's are used. */
    val datesFromServer: Boolean,
    /** False when the session itself isn't on the server (offline, older server, none set). */
    val sessionFromServer: Boolean,
) {
    val label: String get() = "Term $term"

    /** The results scope of this term ("term1" | "term2"). */
    val scope: String get() = if (term == 2) "term2" else "term1"

    /** Whole days after today up to the term's last day: 0 on the last day, negative once it is over. */
    val daysLeft: Long get() = ChronoUnit.DAYS.between(today, end)

    /** Share of the term gone by, today included, 0..1. */
    val elapsed: Float
        get() {
            val total = ChronoUnit.DAYS.between(start, end) + 1
            if (total <= 0) return 1f
            val gone = ChronoUnit.DAYS.between(start, today) + 1
            return (gone.toFloat() / total).coerceIn(0f, 1f)
        }
}

/** The first year of a session name: "2026-27" → 2026. */
internal fun sessionStartYear(name: String): Int? =
    Regex("^\\s*(\\d{4})").find(name)?.groupValues?.get(1)?.toIntOrNull()

private fun isoDate(raw: String?): LocalDate? =
    raw?.trim()?.take(10)?.let { runCatching { LocalDate.parse(it) }.getOrNull() }

/**
 * The term [today] is in for the session in [choice]. The term itself follows
 * [SessionRepository.termScopeFor] (Term 2 from its start date), so Home, Results and
 * Marks always agree. Dates are the session's own; any it doesn't have come from the
 * school calendar the principal confirmed: Term 1 April to September, Term 2 October to
 * March.
 */
fun termInfo(choice: SessionChoice, today: LocalDate): TermInfo {
    val row = choice.currentRow
    val term = if (SessionRepository.termScopeFor(row, today) == "term2") 2 else 1
    val year = sessionStartYear(choice.current) ?: if (today.monthValue >= 4) today.year else today.year - 1
    val calendarStart = if (term == 1) LocalDate.of(year, 4, 1) else LocalDate.of(year, 10, 1)
    val calendarEnd = if (term == 1) LocalDate.of(year, 9, 30) else LocalDate.of(year + 1, 3, 31)
    val serverStart = if (term == 1) isoDate(row?.term1Start) ?: isoDate(row?.startsOn) else isoDate(row?.term2Start)
    val serverEnd = if (term == 1) {
        isoDate(row?.term1End) ?: isoDate(row?.term2Start)?.minusDays(1)
    } else {
        isoDate(row?.term2End) ?: isoDate(row?.endsOn)
    }
    return TermInfo(
        session = choice.current,
        term = term,
        start = serverStart ?: calendarStart,
        end = serverEnd ?: calendarEnd,
        today = today,
        datesFromServer = serverStart != null && serverEnd != null,
        sessionFromServer = choice.fromServer && row != null,
    )
}

// ── Marks progress (admins) and marks to finish (teachers) ─────────────

/** The exams that count in [term]: the term's own and those held in both terms (term null). */
fun List<BatchSummaryItemDto>.inTerm(term: Int): List<BatchSummaryItemDto> =
    filter { it.term == null || it.term == term }

private fun BatchSummaryItemDto.isSubmitted() = status == "submitted"
private fun BatchSummaryItemDto.isDraft() = status == "draft"

/** No marks saved yet ("none", or a status this app doesn't know). */
private fun BatchSummaryItemDto.notStarted() = !isSubmitted() && !isDraft()

/**
 * An exam that has nobody to mark: an optional subject no student takes, or a class with
 * no students. It is never counted as missing, since there is nothing to enter.
 */
private fun BatchSummaryItemDto.nobodyToMark() = notStarted() && classSize <= 0

private val CLASS_RANK: Map<String, Int> = CLASSES.withIndex().associate { (i, c) -> c to i }

/** [names] in school order; a name the app doesn't know goes last, in the order given. */
internal fun <T> List<T>.inSchoolOrder(name: (T) -> String): List<T> =
    sortedBy { CLASS_RANK[name(it)] ?: Int.MAX_VALUE }

/** One class's exams in a term, by state. */
@Immutable
data class ClassMarksProgress(
    val className: String,
    val submitted: Int,
    val draft: Int,
    /** Exams with no marks saved yet (and somebody to mark). */
    val missing: Int,
    /** Exams with an edit request waiting for the super-admin. */
    val pendingEdits: Int,
) {
    val total: Int get() = submitted + draft + missing
}

@Immutable
data class MarksProgress(val session: String, val term: Int, val classes: List<ClassMarksProgress>) {
    val submitted: Int get() = classes.sumOf { it.submitted }
    val draft: Int get() = classes.sumOf { it.draft }
    val missing: Int get() = classes.sumOf { it.missing }
}

/** Per class, in school order, for the term's [items]. */
fun marksProgressByClass(items: List<BatchSummaryItemDto>): List<ClassMarksProgress> =
    items.groupBy { it.className }
        .map { (cls, list) ->
            val counted = list.filterNot { it.nobodyToMark() }
            ClassMarksProgress(
                className = cls,
                submitted = counted.count { it.isSubmitted() },
                draft = counted.count { it.isDraft() },
                missing = counted.count { it.notStarted() },
                pendingEdits = list.count { it.pendingEditRequest },
            )
        }
        .inSchoolOrder { it.className }

/**
 * What a teacher still has to do for the term's marks. The rules:
 *  - ready to submit: a draft with no edit request pending whose every student has an
 *    entry (entered >= class_size > 0), so all that is left is Submit;
 *  - drafts: every other draft without a pending edit request (marks still to enter);
 *  - waiting for approval: an edit request is pending (the batch stays locked until the
 *    super-admin answers);
 *  - not started: no marks saved yet, counted per class.
 * An exam with nobody to mark (an optional subject no student takes) is left out, unless an
 * edit request on it is waiting. Whether a draft is an approved edit waiting to be
 * re-submitted can't be told from the summary, so such a batch shows as ready to submit
 * (or as a draft if marks are missing).
 */
@Immutable
data class MarksTodo(
    val session: String,
    val term: Int,
    val readyToSubmit: List<BatchSummaryItemDto>,
    val drafts: List<BatchSummaryItemDto>,
    val awaitingApproval: List<BatchSummaryItemDto>,
    /** (class, exams with no marks yet), in school order. */
    val notStarted: List<Pair<String, Int>>,
    val submitted: Int,
) {
    val notStartedCount: Int get() = notStarted.sumOf { it.second }
    val allDone: Boolean get() = readyToSubmit.isEmpty() && drafts.isEmpty() && notStartedCount == 0
}

fun marksTodo(session: String, term: Int, items: List<BatchSummaryItemDto>): MarksTodo {
    val toMark = items.filter { it.classSize > 0 }
    fun ready(i: BatchSummaryItemDto) = i.isDraft() && !i.pendingEditRequest && i.entered >= i.classSize
    val notStarted = toMark.filter { it.notStarted() }
        .groupBy { it.className }
        .map { (cls, list) -> cls to list.size }
        .inSchoolOrder { it.first }
    return MarksTodo(
        session = session,
        term = term,
        readyToSubmit = toMark.filter { ready(it) },
        // Fewest marks still missing first: those are the quickest to finish.
        drafts = toMark.filter { it.isDraft() && !it.pendingEditRequest && !ready(it) }
            .sortedBy { it.classSize - it.entered },
        awaitingApproval = items.filter { it.pendingEditRequest },
        notStarted = notStarted,
        submitted = items.count { it.isSubmitted() && !it.pendingEditRequest },
    )
}

// ── Results readiness (teachers) ────────────────────────────────────────

/** How far a class's results for the term have got. */
@Immutable
data class ClassReadiness(
    val className: String,
    val classSize: Int = 0,
    /** Students with a rank (at least one mark in the scope); see [ranksKnown]. */
    val ranked: Int = 0,
    /** False on servers without ranks (results engine v1): [ranked] then counts students with any mark. */
    val ranksKnown: Boolean = true,
    /** Every subject in and nothing in draft: the ranks are final. */
    val complete: Boolean = false,
    val hasDrafts: Boolean = false,
    /** Why this class's results couldn't be read; the other classes still show. */
    val error: String? = null,
)

@Immutable
data class ResultsReadiness(val session: String, val term: Int, val classes: List<ClassReadiness>)

/**
 * How far [cls]'s results have got. Session-18 servers (results engine v1) send no ranks,
 * class size or completeness: their rows are counted instead (students with any mark).
 */
fun ClassResultsDto.readiness(cls: String): ClassReadiness =
    if (engineVersion >= 2) {
        ClassReadiness(
            className = cls,
            classSize = if (classSize > 0) classSize else students.size,
            ranked = rankedCount,
            complete = complete,
            hasDrafts = hasDrafts || students.any { it.draftComponents > 0 },
        )
    } else {
        ClassReadiness(
            className = cls,
            classSize = students.size,
            ranked = students.count { it.hasAnyMarks() },
            ranksKnown = false,
            hasDrafts = students.any { it.draftComponents > 0 },
        )
    }

// ── Fees (admins) ───────────────────────────────────────────────────────

@Immutable
data class FeeReceipt(
    val studentName: String,
    val className: String,
    val amount: BigDecimal,
    /** The day it was paid; null when unreadable. */
    val date: LocalDate?,
    /** What it pays for ("April 2026"). */
    val period: String,
)

@Immutable
data class FeesSummary(
    val month: YearMonth,
    /** Receipts paid from the 1st of the month up to today, as the web dashboard counts them. */
    val total: BigDecimal,
    val count: Int,
    /** The latest three receipts, newest first (of any month). */
    val recent: List<FeeReceipt>,
)

private fun FeePaymentDto.amountValue(): BigDecimal = amount.trim().toBigDecimalOrNull() ?: BigDecimal.ZERO

fun feesSummary(fees: List<FeePaymentDto>, today: LocalDate): FeesSummary {
    val monthStart = today.withDayOfMonth(1)
    val dated = fees.map { it to isoDate(it.date) }
    val thisMonth = dated.filter { (_, d) -> d != null && !d.isBefore(monthStart) && !d.isAfter(today) }
    val recent = dated
        .sortedWith(
            compareByDescending<Pair<FeePaymentDto, LocalDate?>, LocalDate?>(nullsFirst()) { it.second }
                .thenByDescending { it.first.createdAt.orEmpty() }
                .thenByDescending { it.first.id }
        )
        .take(3)
        .map { (f, d) ->
            FeeReceipt(
                studentName = f.studentName.trim(),
                className = f.className.trim(),
                amount = f.amountValue(),
                date = d,
                period = listOf(f.month.trim(), f.year.trim()).filter { it.isNotEmpty() }.joinToString(" "),
            )
        }
    return FeesSummary(
        month = YearMonth.from(today),
        total = thisMonth.fold(BigDecimal.ZERO) { acc, (f, _) -> acc + f.amountValue() },
        count = thisMonth.size,
        recent = recent,
    )
}

// ── Students and staff (admins) ─────────────────────────────────────────

/** Student and staff counts; a count that couldn't be read is null and [error] says why. */
@Immutable
data class Headcount(val students: Int?, val staff: Int?, val error: String? = null)

@Immutable
data class ClassSize(val className: String, val size: Int)

/** The smallest and largest class that has students; null when no class has any. */
fun List<ClassAttendanceRowDto>.sizeExtremes(): Pair<ClassSize, ClassSize>? {
    val withStudents = filter { it.classSize > 0 }
    if (withStudents.isEmpty()) return null
    val min = withStudents.minBy { it.classSize }
    val max = withStudents.maxBy { it.classSize }
    return ClassSize(min.className, min.classSize) to ClassSize(max.className, max.classSize)
}

// ── Formatting ──────────────────────────────────────────────────────────

/**
 * A percentage as the server rounds it (one decimal): "80.8%", "100%". Built by hand, not
 * with String.format, so a device locale can't change the digits or the decimal mark.
 */
fun formatPercent(percent: Double): String {
    val tenths = (percent * 10).roundToLong()
    val whole = tenths / 10
    val frac = abs(tenths % 10)
    return if (frac == 0L) "$whole%" else "$whole.$frac%"
}

/** The same, for TalkBack: "80.8 percent". */
fun spokenPercent(percent: Double): String = formatPercent(percent).removeSuffix("%") + " percent"

/**
 * Rupees with Indian digit grouping and no paise when there are none: "₹1,23,500", "₹1,500.50".
 * Android's ICU formatter, which groups lakhs and crores (java.text on a desktop JVM doesn't).
 */
fun formatRupees(amount: BigDecimal): String {
    val format = NumberFormat.getCurrencyInstance(Locale("en", "IN"))
    val whole = amount.signum() == 0 || amount.stripTrailingZeros().scale() <= 0
    format.minimumFractionDigits = if (whole) 0 else 2
    format.maximumFractionDigits = if (whole) 0 else 2
    return format.format(amount)
}

/** "1 class", "4 classes", "2 days": [n] and the noun, plural unless n is 1. */
fun plural(n: Int, one: String, many: String = regularPlural(one)): String = "$n ${if (n == 1) one else many}"

private fun regularPlural(one: String): String =
    if (one.endsWith("s") || one.endsWith("sh") || one.endsWith("ch") || one.endsWith("x")) one + "es" else one + "s"

/**
 * A page of the web portal, from the app's API base URL: the portal lives at /admin/ next
 * to /api/ ("https://kisschool.in/api/" + "fees" → "https://kisschool.in/admin/fees"; TEST
 * keeps its /kisschool prefix the same way).
 */
fun portalPageUrl(apiBaseUrl: String, page: String): String =
    apiBaseUrl.trimEnd('/').removeSuffix("/api") + "/admin/" + page.trimStart('/')
