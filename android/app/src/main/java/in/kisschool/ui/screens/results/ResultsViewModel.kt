package `in`.kisschool.ui.screens.results

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.AcademicSessionDto
import `in`.kisschool.data.api.dto.ClassResultsDto
import `in`.kisschool.data.api.dto.StudentResultDto
import `in`.kisschool.data.repo.FeatureUnavailableException
import `in`.kisschool.data.repo.ReportCardRepository
import `in`.kisschool.data.repo.ResultsRepository
import `in`.kisschool.data.repo.SessionRepository
import `in`.kisschool.data.repo.userMessage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** The three result scopes, as the API names them. */
enum class ResultScope(val key: String, val label: String) {
    TERM1("term1", "Term 1"),
    TERM2("term2", "Term 2"),
    ANNUAL("annual", "Annual");

    companion object {
        fun of(key: String): ResultScope = ResultScope.entries.firstOrNull { it.key == key } ?: TERM1
    }
}

/** Whether a report card can be made for the selected class, session and scope. */
sealed interface CardTemplateState {
    /** Nothing checked yet (no class picked). */
    data object Idle : CardTemplateState
    data object Checking : CardTemplateState
    /** The class has no report-card template for this session and scope yet. */
    data object Missing : CardTemplateState
    data class Ready(val templateId: Long) : CardTemplateState
    /** Can't tell or can't make one: older server, no access, offline. */
    data class Unavailable(val message: String) : CardTemplateState
}

/** A card that finished downloading and should open in the preview. */
data class OpenCard(val studentId: Long, val name: String)

/** Why a student's report card couldn't be made; shown only in that student's sheet. */
data class CardError(val studentId: Long, val message: String)

data class ResultsUiState(
    val classOptions: List<String> = emptyList(),
    val cls: String? = null,
    val sessionOptions: List<String> = emptyList(),
    val session: String = SessionRepository.fallbackSessionName(),
    val scope: ResultScope = ResultScope.TERM1,
    /** Why the scope changed on its own, e.g. no Term 2 marks yet. */
    val scopeNote: String? = null,
    val results: ClassResultsDto? = null,
    val loading: Boolean = false,
    val error: String? = null,
    /** Student whose details sheet is open. */
    val selectedStudentId: Long? = null,
    val cardTemplate: CardTemplateState = CardTemplateState.Idle,
    /** Student whose card is being made (one at a time), and their name. */
    val cardBusyFor: Long? = null,
    val cardBusyName: String = "",
    val cardError: CardError? = null,
    val openCard: OpenCard? = null,
) {
    val selectedStudent: StudentResultDto?
        get() = selectedStudentId?.let { id -> results?.students?.firstOrNull { it.studentId == id } }
}

/** True when the student has at least one mark or letter in the scope (v1 servers have no has_marks). */
internal fun StudentResultDto.hasAnyMarks(): Boolean =
    hasMarks || subjects.any { it.status != "missing" }

class ResultsViewModel(
    private val resultsRepo: ResultsRepository,
    private val sessionRepo: SessionRepository,
    private val reportCardRepo: ReportCardRepository,
    classOptions: List<String>,
) : ViewModel() {

    private val _state = MutableStateFlow(
        ResultsUiState(
            classOptions = classOptions,
            cls = classOptions.firstOrNull(),
            scope = ResultScope.of(SessionRepository.termScopeFor(null)),
            // The first load waits for the session list; show a spinner, not "pick a class".
            loading = classOptions.isNotEmpty(),
        )
    )
    val state: StateFlow<ResultsUiState> = _state.asStateFlow()

    /** True once the teacher picks a scope; until then each class and session starts on the current term. */
    private var scopePicked = false
    /** The current session's row: its Term 2 start decides the automatic scope. */
    private var currentRow: AcademicSessionDto? = null
    private var sessionTouched = false
    private var resultsJob: Job? = null
    private var templateJob: Job? = null
    private var cardJob: Job? = null
    /** Goes up whenever a card job starts or is dropped, so a dropped one can never land. */
    private var cardSeq = 0

    private fun set(block: (ResultsUiState) -> ResultsUiState) { _state.value = block(_state.value) }

    init {
        viewModelScope.launch {
            val choice = sessionRepo.choice()
            currentRow = choice.currentRow
            if (!sessionTouched) {
                set { it.copy(sessionOptions = choice.names, session = choice.current) }
            } else {
                set { it.copy(sessionOptions = choice.names) }
            }
            reload()        // also puts the scope on the current term
        }
    }

    fun selectClass(c: String) {
        if (c == _state.value.cls && _state.value.results != null) return
        set { it.copy(cls = c) }
        reload()
    }

    fun selectSession(name: String) {
        sessionTouched = true
        if (name == _state.value.session && _state.value.results != null) return
        set { it.copy(session = name) }
        reload()
    }

    fun selectScope(scope: ResultScope) {
        scopePicked = true
        if (scope == _state.value.scope && _state.value.results != null) {
            set { it.copy(scopeNote = null) }
            return
        }
        set { it.copy(scope = scope, scopeNote = null) }
        reload()
    }

    /**
     * Re-fetch results and the template check for the current selection (a new class or
     * session, Refresh, Try again). Until the teacher picks a scope, each one starts on
     * the current term again, so its own Term 2 check (and note) is made afresh.
     */
    fun reload() {
        if (!scopePicked) {
            set { it.copy(scope = ResultScope.of(SessionRepository.termScopeFor(currentRow)), scopeNote = null) }
        }
        load()
    }

    private fun load() {
        val s = _state.value
        val cls = s.cls ?: return
        val session = s.session
        val scope = s.scope
        resultsJob?.cancel()
        dropCard()      // the sheet closes, and the card it was for belongs to the old selection
        set {
            it.copy(
                loading = true, error = null, results = null,
                selectedStudentId = null, cardError = null,
            )
        }
        resultsJob = viewModelScope.launch {
            try {
                val r = resultsRepo.classResults(cls, session, scope.key)
                // Early in Term 2 there is nothing to show yet: fall back to Term 1 for this
                // class and session, and say so. Never overrides a scope the teacher picked.
                if (!scopePicked && scope == ResultScope.TERM2 && r.students.none { it.hasAnyMarks() }) {
                    set { it.copy(scope = ResultScope.TERM1, scopeNote = "No Term 2 marks yet, so Term 1 is shown.") }
                    load()
                    return@launch
                }
                set { it.copy(loading = false, results = r) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set { it.copy(loading = false, error = e.userMessage("Couldn't load results")) }
            }
        }
        checkTemplate(cls, session, scope)
    }

    private fun checkTemplate(cls: String, session: String, scope: ResultScope) {
        templateJob?.cancel()
        set { it.copy(cardTemplate = CardTemplateState.Checking) }
        templateJob = viewModelScope.launch {
            val next = try {
                val t = reportCardRepo.resolveTemplate(cls, session, scope.key)
                if (t == null) CardTemplateState.Missing else CardTemplateState.Ready(t.id)
            } catch (e: CancellationException) {
                throw e
            } catch (e: FeatureUnavailableException) {
                CardTemplateState.Unavailable(e.message ?: "Report cards aren't available on this server yet.")
            } catch (e: Exception) {
                CardTemplateState.Unavailable(e.userMessage("Couldn't check for a report-card template"))
            }
            set { it.copy(cardTemplate = next) }
        }
    }

    fun openStudent(studentId: Long) {
        // A card still being made for someone else is dropped: one sheet, one student.
        if (_state.value.cardBusyFor.let { it != null && it != studentId }) dropCard()
        set { it.copy(selectedStudentId = studentId, cardError = null) }
    }

    /** Closing the sheet stops waiting for its card; the server still caches it, so a retry is quick. */
    fun closeStudent() {
        dropCard()
        set { it.copy(selectedStudentId = null, cardError = null) }
    }

    private fun dropCard() {
        cardSeq++
        cardJob?.cancel()
        cardJob = null
        set { it.copy(cardBusyFor = null, cardBusyName = "") }
    }

    /**
     * Render + download a student's card. On success [ResultsUiState.openCard] is set, but
     * only while that student's sheet is still open; a failure is kept for that student.
     */
    fun makeReportCard(studentId: Long) {
        val s = _state.value
        val templateId = (s.cardTemplate as? CardTemplateState.Ready)?.templateId ?: return
        if (s.cardBusyFor != null) return
        val name = s.results?.students?.firstOrNull { it.studentId == studentId }?.name.orEmpty()
        val seq = ++cardSeq
        set { it.copy(cardBusyFor = studentId, cardBusyName = name, cardError = null) }
        cardJob = viewModelScope.launch {
            try {
                reportCardRepo.prepare(templateId, studentId)
                set {
                    if (seq != cardSeq) it
                    else it.copy(
                        cardBusyFor = null, cardBusyName = "",
                        openCard = if (it.selectedStudentId == studentId) OpenCard(studentId, name) else it.openCard,
                    )
                }
            } catch (e: CancellationException) {
                set { if (seq != cardSeq) it else it.copy(cardBusyFor = null, cardBusyName = "") }
                throw e
            } catch (e: Exception) {
                set {
                    if (seq != cardSeq) it
                    else it.copy(
                        cardBusyFor = null, cardBusyName = "",
                        cardError = CardError(studentId, e.userMessage("Couldn't make the report card")),
                    )
                }
            }
        }
    }

    /** The screen has navigated to the preview. */
    fun consumeOpenCard() {
        set { it.copy(openCard = null) }
    }
}
