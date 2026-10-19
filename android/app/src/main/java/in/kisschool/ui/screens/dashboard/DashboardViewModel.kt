package `in`.kisschool.ui.screens.dashboard

import android.os.SystemClock
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.ClassAttendanceSummaryDto
import `in`.kisschool.data.repo.ApprovalCounts
import `in`.kisschool.data.repo.AttendanceRepository
import `in`.kisschool.data.repo.DashboardRepository
import `in`.kisschool.data.repo.FeatureUnavailableException
import `in`.kisschool.data.repo.Notice
import `in`.kisschool.data.repo.NoticeRepository
import `in`.kisschool.data.repo.ResultsRepository
import `in`.kisschool.data.repo.SessionChoice
import `in`.kisschool.data.repo.SessionRepository
import `in`.kisschool.data.repo.attemptCall
import `in`.kisschool.data.repo.userMessage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Deferred
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
import kotlinx.coroutines.awaitAll
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth

/** The month calendar that opens under a class in the class-wise attendance card. */
data class DashboardUiState(
    val allowedClasses: List<String> = emptyList(),
    /** The class whose month calendar is open; null while none is. */
    val selectedClass: String? = null,
    val month: YearMonth = YearMonth.now(),
    /** ISO dates in the displayed month that have student attendance. */
    val markedDates: Set<String> = emptySet(),
    /** ISO dates flagged as holidays. */
    val holidays: Set<String> = emptySet(),
    val loading: Boolean = false,
    val error: String? = null,
)

/** Every card's data. Each card loads on its own, so one slow or failing read holds up nothing else. */
data class DashboardCards(
    /** The day "today" means for every card, fixed at the last refresh. */
    val today: LocalDate = LocalDate.now(),
    val access: DashboardAccess = DashboardAccess(),
    /** Every class in scope, today (the hero rings, the chips, class sizes, Today's bars). */
    val todaySummary: Loadable<ClassAttendanceSummaryDto> = Loadable(),
    /** The class-wise card's period; Today reuses [todaySummary]. */
    val period: AttendancePeriod = AttendancePeriod.TODAY,
    val periodSummary: Loadable<ClassAttendanceSummaryDto> = Loadable(),
    val term: Loadable<TermInfo> = Loadable(),
    val approvals: Loadable<ApprovalCounts> = Loadable(),
    val marksProgress: Loadable<MarksProgress> = Loadable(),
    val fees: Loadable<FeesSummary> = Loadable(),
    val headcount: Loadable<Headcount> = Loadable(),
    /** The latest three. */
    val notices: Loadable<List<Notice>> = Loadable(),
    val marksTodo: Loadable<MarksTodo> = Loadable(),
    val readiness: Loadable<ResultsReadiness> = Loadable(),
) {
    /** What the class-wise attendance card draws for the picked period. */
    val barsSummary: Loadable<ClassAttendanceSummaryDto>
        get() = if (period == AttendancePeriod.TODAY) todaySummary else periodSummary

    /** True while any card is loading (the top bar's refresh button shows a spinner). */
    val anyLoading: Boolean
        get() = listOf(
            todaySummary, periodSummary, term, approvals, marksProgress, fees,
            headcount, notices, marksTodo, readiness,
        ).any { it.loading }
}

/** The dashboard's cards, for retrying one. */
enum class DashCard { TODAY, PERIOD, TERM, APPROVALS, MARKS_PROGRESS, FEES, HEADCOUNT, NOTICES, MARKS_TODO, READINESS }

/**
 * Drives the Home dashboard: one independent load per card (its own loading, error and
 * "not on this server" state), the class-wise card's period, and the month calendar that
 * opens under a class (one request per class and month, from GET /attendance/marked-dates;
 * MonthCalendar works out marked / missed / off / future per day).
 *
 * Admins and the super-admin get the school-wide cards; a teacher gets their own classes'
 * cards, and the marks cards only with the matching menu grant ([DashboardAccess]).
 */
class DashboardViewModel(
    private val attendanceRepo: AttendanceRepository,
    private val dashboardRepo: DashboardRepository,
    private val sessionRepo: SessionRepository,
    private val noticeRepo: NoticeRepository,
    private val resultsRepo: ResultsRepository,
    allowedClasses: List<String>,
    access: DashboardAccess,
) : ViewModel() {

    private val _state = MutableStateFlow(
        DashboardUiState(
            allowedClasses = allowedClasses,
            // A teacher with one class sees its month straight away.
            selectedClass = allowedClasses.singleOrNull(),
        )
    )
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    private val _cards = MutableStateFlow(DashboardCards(access = access))
    val cards: StateFlow<DashboardCards> = _cards.asStateFlow()

    private val jobs = HashMap<DashCard, Job>()
    /** The latest load of each card; a reply from an older load is dropped. */
    private val tokens = HashMap<DashCard, Any>()
    private var monthJob: Job? = null
    /** The current session, shared by the cards that need it within one refresh. */
    private var session: Deferred<SessionChoice>? = null
    private var refreshedAt = 0L
    private var approvalsAt = 0L

    init {
        refreshAll()
    }

    // ── Who is looking ──────────────────────────────────────────────────

    /**
     * The signed-in user's classes and access as /auth/me now has them. A different role
     * gets its own cards, all loaded afresh; new classes reload the cards that show them.
     */
    fun configure(classes: List<String>, access: DashboardAccess) {
        val sameAccess = access == _cards.value.access
        if (sameAccess && classes == _state.value.allowedClasses) return
        setClasses(classes)
        if (!sameAccess) {
            jobs.values.forEach { it.cancel() }
            jobs.clear()
            tokens.clear()
            _cards.value = DashboardCards(today = _cards.value.today, access = access, period = _cards.value.period)
        }
        refreshAll()
    }

    // ── Refreshing ──────────────────────────────────────────────────────

    /** Reload every card the user has, and the open month calendar (the top bar's refresh). */
    fun refreshAll() {
        refreshedAt = SystemClock.elapsedRealtime()
        val today = LocalDate.now()
        if (today != _cards.value.today) _cards.update { it.copy(today = today) }
        session?.cancel()
        session = newSession()
        val access = _cards.value.access
        loadToday()
        loadPeriod()
        loadTerm()
        loadNotices()
        if (access.isAdmin) {
            loadApprovals()
            loadMarksProgress()
            loadFees()
            loadHeadcount()
        } else {
            loadMarksTodo()
            loadReadiness()
        }
        loadMonth()
    }

    /** Attendance was saved on another screen: the attendance cards and the open calendar reload. */
    fun onAttendanceChanged() {
        loadToday()
        loadPeriod()
        loadMonth()
    }

    /**
     * Home is showing again (back from another screen, or the app reopened). Everything
     * reloads once the data is a few minutes old or the date has changed; the approval
     * counts reload each time, since the super-admin may have just cleared some.
     */
    fun onResumed() {
        val now = SystemClock.elapsedRealtime()
        when {
            LocalDate.now() != _cards.value.today || now - refreshedAt >= STALE_AFTER_MS -> refreshAll()
            now - approvalsAt >= APPROVALS_FRESH_MS -> loadApprovals()
        }
    }

    /** One card's "Try again". */
    fun retry(card: DashCard) {
        when (card) {
            DashCard.TODAY -> loadToday()
            DashCard.PERIOD -> loadPeriod()
            DashCard.APPROVALS -> loadApprovals()
            DashCard.FEES -> loadFees()
            DashCard.HEADCOUNT -> loadHeadcount()
            DashCard.NOTICES -> loadNotices()
            // These read the session first: ask for it again, in case that is what failed.
            DashCard.TERM, DashCard.MARKS_PROGRESS, DashCard.MARKS_TODO, DashCard.READINESS -> {
                session = newSession()
                when (card) {
                    DashCard.TERM -> loadTerm()
                    DashCard.MARKS_PROGRESS -> loadMarksProgress()
                    DashCard.MARKS_TODO -> loadMarksTodo()
                    else -> loadReadiness()
                }
            }
        }
    }

    /** Show the class-wise card for [p] (Today reuses today's summary, already loaded). */
    fun selectPeriod(p: AttendancePeriod) {
        if (p == _cards.value.period) return
        jobs.remove(DashCard.PERIOD)?.cancel()
        tokens.remove(DashCard.PERIOD)
        // The last period's numbers don't belong under the new chip, not even dimmed.
        _cards.update { it.copy(period = p, periodSummary = Loadable()) }
        loadPeriod()
    }

    // ── The cards ───────────────────────────────────────────────────────

    private fun newSession(): Deferred<SessionChoice> {
        val today = _cards.value.today
        // SessionRepository.choice never throws (it falls back to the April-rollover name).
        return viewModelScope.async { sessionRepo.choice(today) }
    }

    private fun sessionChoice(): Deferred<SessionChoice> {
        val current = session
        if (current != null && !current.isCancelled) return current
        return newSession().also { session = it }
    }

    /**
     * Start [card]'s load: its data stays while it runs (dimmed on screen), a failure keeps
     * the data with an error above it, and [FeatureUnavailableException] (an older server)
     * turns the card into a one-line note.
     */
    private fun <T> launchCard(
        card: DashCard,
        fallback: String,
        get: (DashboardCards) -> Loadable<T>,
        put: (DashboardCards, Loadable<T>) -> DashboardCards,
        block: suspend () -> T,
    ) {
        jobs.remove(card)?.cancel()
        val token = Any()
        tokens[card] = token
        _cards.update { put(it, get(it).copy(loading = true, error = null)) }
        jobs[card] = viewModelScope.launch {
            val next: Loadable<T> = try {
                Loadable(data = block())
            } catch (e: CancellationException) {
                throw e
            } catch (e: FeatureUnavailableException) {
                Loadable(unavailable = e.message ?: "This server doesn't offer this yet.")
            } catch (e: Exception) {
                get(_cards.value).copy(loading = false, error = e.userMessage(fallback))
            }
            if (tokens[card] === token) _cards.update { put(it, next) }
        }
    }

    private fun loadToday() {
        val day = _cards.value.today
        launchCard(
            DashCard.TODAY, "Couldn't load today's attendance",
            { it.todaySummary }, { c, l -> c.copy(todaySummary = l) },
        ) { dashboardRepo.classSummary(day, day) }
    }

    private fun loadPeriod() {
        val period = _cards.value.period
        if (period == AttendancePeriod.TODAY) return
        val (from, to) = period.range(_cards.value.today)
        launchCard(
            DashCard.PERIOD, "Couldn't load attendance for ${period.label.lowercase()}",
            { it.periodSummary }, { c, l -> c.copy(periodSummary = l) },
        ) { dashboardRepo.classSummary(from, to) }
    }

    private fun loadTerm() {
        val today = _cards.value.today
        val choice = sessionChoice()
        launchCard(
            DashCard.TERM, "Couldn't load the session",
            { it.term }, { c, l -> c.copy(term = l) },
        ) { termInfo(choice.await(), today) }
    }

    private fun loadApprovals() {
        if (!_cards.value.access.isSuperAdmin) return
        approvalsAt = SystemClock.elapsedRealtime()
        launchCard(
            DashCard.APPROVALS, "Couldn't load approvals",
            { it.approvals }, { c, l -> c.copy(approvals = l) },
        ) { dashboardRepo.approvalCounts() }
    }

    private fun loadMarksProgress() {
        if (!_cards.value.access.isAdmin) return
        val today = _cards.value.today
        val choice = sessionChoice()
        launchCard(
            DashCard.MARKS_PROGRESS, "Couldn't load marks progress",
            { it.marksProgress }, { c, l -> c.copy(marksProgress = l) },
        ) {
            val sc = choice.await()
            val term = termInfo(sc, today).term
            val summary = dashboardRepo.marksSummary(sc.current)
            MarksProgress(session = sc.current, term = term, classes = marksProgressByClass(summary.items.inTerm(term)))
        }
    }

    private fun loadFees() {
        if (!_cards.value.access.isAdmin) return
        val today = _cards.value.today
        launchCard(
            DashCard.FEES, "Couldn't load fees",
            { it.fees }, { c, l -> c.copy(fees = l) },
        ) { feesSummary(dashboardRepo.fees(), today) }
    }

    private fun loadHeadcount() {
        if (!_cards.value.access.isAdmin) return
        launchCard(
            DashCard.HEADCOUNT, "Couldn't load the student and staff counts",
            { it.headcount }, { c, l -> c.copy(headcount = l) },
        ) {
            coroutineScope {
                val students = async { attemptCall { dashboardRepo.studentTotal() } }
                val staff = async { attemptCall { dashboardRepo.staffCount() } }
                val s = students.await()
                val st = staff.await()
                val failure = s.exceptionOrNull() ?: st.exceptionOrNull()
                if (failure != null && s.isFailure && st.isFailure) throw failure
                Headcount(
                    students = s.getOrNull(),
                    staff = st.getOrNull(),
                    error = failure?.userMessage("Couldn't load every count"),
                )
            }
        }
    }

    private fun loadNotices() {
        launchCard(
            DashCard.NOTICES, "Couldn't load notices",
            { it.notices }, { c, l -> c.copy(notices = l) },
        ) { noticeRepo.list().take(3) }
    }

    private fun loadMarksTodo() {
        val access = _cards.value.access
        if (access.isAdmin || !access.canMarksEntry) return
        val today = _cards.value.today
        val choice = sessionChoice()
        launchCard(
            DashCard.MARKS_TODO, "Couldn't load your marks",
            { it.marksTodo }, { c, l -> c.copy(marksTodo = l) },
        ) {
            val sc = choice.await()
            val term = termInfo(sc, today).term
            // The server lists the teacher's own classes only.
            val summary = dashboardRepo.marksSummary(sc.current)
            marksTodo(sc.current, term, summary.items.inTerm(term))
        }
    }

    private fun loadReadiness() {
        val access = _cards.value.access
        if (access.isAdmin || !access.canResults) return
        val today = _cards.value.today
        val classes = _state.value.allowedClasses
        val choice = sessionChoice()
        launchCard(
            DashCard.READINESS, "Couldn't load results",
            { it.readiness }, { c, l -> c.copy(readiness = l) },
        ) {
            val sc = choice.await()
            val info = termInfo(sc, today)
            val results = coroutineScope {
                classes.map { cls ->
                    async { attemptCall { resultsRepo.classResults(cls, sc.current, info.scope) } }
                }.awaitAll()
            }
            // Every class answering "not on this server" is the server, not the classes.
            val unavailable = results.map { it.exceptionOrNull() }
            if (unavailable.isNotEmpty() && unavailable.all { it is FeatureUnavailableException }) {
                throw unavailable.first()!!
            }
            ResultsReadiness(
                session = sc.current,
                term = info.term,
                classes = classes.zip(results) { cls, r ->
                    r.fold(
                        onSuccess = { it.readiness(cls) },
                        onFailure = { ClassReadiness(cls, error = it.userMessage("Couldn't load results")) },
                    )
                },
            )
        }
    }

    // ── The month calendar under a class ────────────────────────────────

    /** Open [c]'s month calendar in the class-wise card (on this month), or close it when it is open. */
    fun toggleClass(c: String) {
        val cur = _state.value
        monthJob?.cancel()
        _state.value = if (cur.selectedClass == c) {
            cur.copy(selectedClass = null, markedDates = emptySet(), holidays = emptySet(), loading = false, error = null)
        } else {
            cur.copy(
                selectedClass = c, month = YearMonth.now(),
                markedDates = emptySet(), holidays = emptySet(), loading = false, error = null,
            )
        }
        loadMonth()
    }

    /**
     * Replace the class list, e.g. once /auth/me has filled in a role or class grants the
     * app didn't have when Home opened. An open calendar stays open while its class is still
     * offered; a teacher with a single class has it open from the start.
     */
    fun setClasses(classes: List<String>) {
        val cur = _state.value
        if (classes == cur.allowedClasses) return
        val next = cur.selectedClass?.takeIf { it in classes } ?: classes.singleOrNull()
        if (next == cur.selectedClass) {
            _state.value = cur.copy(allowedClasses = classes)
            return
        }
        monthJob?.cancel()
        _state.value = cur.copy(
            allowedClasses = classes,
            selectedClass = next,
            month = YearMonth.now(),
            // The previous class's month no longer applies.
            markedDates = emptySet(),
            holidays = emptySet(),
            loading = false,
            error = null,
        )
        loadMonth()
    }

    fun prevMonth() {
        _state.update { it.copy(month = it.month.minusMonths(1)) }
        loadMonth()
    }

    fun nextMonth() {
        _state.update { it.copy(month = it.month.plusMonths(1)) }
        loadMonth()
    }

    /** Re-fetch the displayed month (e.g. after marking attendance from a day tap). */
    fun reloadCurrentMonth() = loadMonth()

    private fun loadMonth() {
        val cls = _state.value.selectedClass ?: return
        val ym = _state.value.month
        monthJob?.cancel()
        _state.update { it.copy(loading = true, error = null) }
        monthJob = viewModelScope.launch {
            // A reply for a class or month the user has since left is dropped: the load for
            // the current pick is still running and will fill the calendar in.
            fun stillShown() = _state.value.selectedClass == cls && _state.value.month == ym
            try {
                val cov = attendanceRepo.markedDates(cls, ym.atDay(1).toString(), ym.atEndOfMonth().toString())
                if (!stillShown()) return@launch
                _state.update { it.copy(markedDates = cov.marked, holidays = cov.holidays, loading = false) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                if (!stillShown()) return@launch
                _state.update { it.copy(loading = false, error = e.userMessage("Couldn't load the month's attendance")) }
            }
        }
    }

    private companion object {
        /** Home reloads everything when it shows again after this long. */
        const val STALE_AFTER_MS = 2 * 60_000L
        /** ...and the approval counts after this long (just not twice on opening). */
        const val APPROVALS_FRESH_MS = 5_000L
    }
}
