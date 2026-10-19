package `in`.kisschool.ui.screens.marks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.BatchDetailDto
import `in`.kisschool.data.api.dto.BatchSaveBody
import `in`.kisschool.data.api.dto.ClassSubjectDetailDto
import `in`.kisschool.data.api.dto.ClassSubjectDto
import `in`.kisschool.data.api.dto.ExamComponentDto
import `in`.kisschool.data.api.dto.MarkItemIn
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.api.dto.SubjectEnrollmentsDto
import `in`.kisschool.data.repo.ApiException
import `in`.kisschool.data.repo.MarksRepository
import `in`.kisschool.data.repo.MetaRepository
import `in`.kisschool.data.repo.SessionRepository
import `in`.kisschool.data.repo.StudentRepository
import `in`.kisschool.data.repo.userMessage
import `in`.kisschool.ui.screens.studentedit.CLASSES
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

/** Max marks are at most 1000 on the server, so four digits is plenty. */
private const val MAX_MARK_DIGITS = 4

/** A saved batch's rows as on-screen entries: the letter for a graded exam, else the marks. */
private fun entriesOf(batch: BatchDetailDto?, graded: Boolean): Map<Long, String> =
    batch?.items.orEmpty().associate { row ->
        row.studentId to if (graded) row.grade.orEmpty() else row.marks.toString()
    }

/** Who takes [this] subject: null when the whole class does, else an optional subject's enrolled students. */
private fun ClassSubjectDto.takers(): Set<Long>? = if (isOptional) enrolledStudentIds.toSet() else null

/** [s] with who takes subject [subjectId] as the server has it now. */
private fun withTakers(s: MarksUiState, subjectId: Long, isOptional: Boolean, studentIds: List<Long>): MarksUiState {
    fun fresh(sub: ClassSubjectDto) =
        if (sub.id == subjectId) sub.copy(isOptional = isOptional, enrolledStudentIds = studentIds) else sub
    return s.copy(subjects = s.subjects.map(::fresh), subject = s.subject?.let(::fresh))
}

/**
 * [s] with the subject (its name and who takes it) and its tests as Class Subjects has
 * them now, keeping the selected test by id (null when it was removed).
 */
private fun withTests(s: MarksUiState, detail: ClassSubjectDetailDto): MarksUiState {
    val tests = detail.components.sortedBy { it.orderIndex }
    fun renamed(sub: ClassSubjectDto) = if (sub.id == detail.id) {
        sub.copy(
            subjectName = detail.subjectName,
            isOptional = detail.isOptional, enrolledStudentIds = detail.enrolledStudentIds,
        )
    } else sub
    return s.copy(
        subjects = s.subjects.map(::renamed),
        subject = s.subject?.let(::renamed),
        components = tests,
        component = s.component?.let { c -> tests.firstOrNull { it.id == c.id } },
    )
}

/**
 * The 400 for a save made with a test as it was before Class Subjects changed it:
 * another max ("Max marks for … is now …"), or a renamed or removed test or subject
 * ("… is not an exam component of …").
 */
private fun Exception.testsChanged(): Boolean {
    val e = this as? ApiException ?: return false
    val msg = e.message.orEmpty()
    return e.code == 400 && (msg.startsWith("Max marks for") || msg.contains("is not an exam component"))
}

/**
 * The 422 for a save that carried marks for students who don't take an optional subject
 * ("… don't take Mathematics (an optional subject). …"): the subject became optional, or
 * who takes it changed, after this screen loaded it.
 */
private fun Exception.notTaken(): Boolean {
    val e = this as? ApiException ?: return false
    return e.code == 422 && e.message.orEmpty().contains("(an optional subject)")
}

/** Why a save didn't go ahead: who takes [subject] changed on the website (the list on screen is the new one). */
private fun takersChangedMessage(subject: String, now: SubjectEnrollmentsDto): String {
    if (!now.isOptional) {
        return "$subject is no longer an optional subject, so the whole class is listed now. Check the marks, then save again."
    }
    return when (val n = now.studentIds.size) {
        0 -> "Who takes $subject was changed on the website: no student takes it now, so there are no marks to save."
        1 -> "Who takes $subject was changed on the website: 1 student takes it now. Check the list, then save again."
        else -> "Who takes $subject was changed on the website: $n students take it now. Check the list, then save again."
    }
}

data class MarksUiState(
    val classOptions: List<String> = CLASSES,
    val cls: String? = null,
    val subjects: List<ClassSubjectDto> = emptyList(),
    val subject: ClassSubjectDto? = null,
    val components: List<ExamComponentDto> = emptyList(),
    val component: ExamComponentDto? = null,
    /** Until the server answers, the April-rollover name for today (Jan–Mar → last year's session). */
    val session: String = SessionRepository.fallbackSessionName(),
    /** Sessions the server lists; empty → the session is a free-text field (offline / older server). */
    val sessionOptions: List<String> = emptyList(),
    val gradeLetters: List<String> = MetaRepository.FALLBACK_GRADE_LETTERS,
    val isSuperAdmin: Boolean = false,
    val students: List<StudentDto> = emptyList(),
    /** Per student: digits for a numeric component, a letter for a graded one; "" = not entered. */
    val marks: Map<Long, String> = emptyMap(),
    val batch: BatchDetailDto? = null,
    /**
     * The selection whose saved marks [marks] and [batch] hold; null until a load
     * succeeds. Saving needs it to match [key]: the server deletes every saved row a
     * save leaves out, so marks from another selection, or from a load that never
     * landed, must never be sent.
     */
    val loadedKey: BatchKey? = null,
    val loadingRoster: Boolean = false,
    val loadingBatch: Boolean = false,
    /** The last batch load failed: the screen offers a retry instead of an empty roster. */
    val batchLoadFailed: Boolean = false,
    val busy: Boolean = false,
    val error: String? = null,
    val message: String? = null,
) {
    val maxMarks: Int get() = component?.maxMarks ?: 0
    /** A max of 0 marks a graded exam ("Term 1 Grade"): each student gets a letter. */
    val isGraded: Boolean get() = component != null && maxMarks == 0
    val locked: Boolean get() = batch?.status == "submitted"
    /** Super-admin edits submitted batches in place; everyone else must request an edit. */
    val lockedForMe: Boolean get() = locked && !isSuperAdmin
    val pending: Boolean get() = batch?.pendingEditRequestId != null
    val editable: Boolean get() = !lockedForMe && !pending
    /**
     * Who takes the selected subject: null when the whole class does, else the students
     * enrolled on an optional subject (11th/12th Mathematics). Only they are listed, and a
     * save carries only their marks: the server refuses marks for anyone else and leaves
     * other students' saved rows alone.
     */
    val takers: Set<Long>? get() = subject?.takers()
    val optional: Boolean get() = takers != null
    /** An optional subject no student takes yet: there is nobody to enter marks for. */
    val noTakers: Boolean get() = takers?.isEmpty() == true
    /** The students marks are entered for, in roll order: the class, or an optional subject's takers. */
    val roster: List<StudentDto> get() = takers?.let { t -> students.filter { it.id in t } } ?: students
    /** The entries a save carries: all of [marks], or only an optional subject's takers'. */
    val entries: Map<Long, String> get() = forTakers(marks)
    private fun forTakers(m: Map<Long, String>): Map<Long, String> =
        takers?.let { t -> m.filterKeys { it in t } } ?: m
    val enteredCount: Int get() = entries.values.count { it.isNotBlank() }
    val overMaxCount: Int
        get() = if (isGraded) 0
        else entries.values.count { it.isNotBlank() && (it.toIntOrNull() ?: Int.MAX_VALUE) > maxMarks }
    /** The batch the selection names; null until class, subject, test and session are all set. */
    val key: BatchKey?
        get() {
            val c = cls ?: return null
            val sub = subject ?: return null
            val comp = component ?: return null
            return if (session.isBlank()) null else BatchKey(c, sub.id, comp.id, session)
        }
    val ready: Boolean get() = key != null
    /** This selection's saved marks are on screen: loaded, and no load running. */
    val marksLoaded: Boolean get() = !loadingBatch && loadedKey != null && loadedKey == key
    /** Rows take input only once this selection's saved marks are on screen. */
    val canEdit: Boolean get() = marksLoaded && editable && !busy
    val canSave: Boolean get() = canEdit && overMaxCount == 0 && !noTakers
    val canSubmit: Boolean get() = canSave && !locked && enteredCount > 0
    /**
     * Marks typed on screen that aren't saved yet. Changing class, subject, test or
     * session, or leaving the screen, would lose them, so the screen asks first.
     */
    val dirty: Boolean
        get() = marksLoaded &&
            entries.filterValues { it.isNotBlank() } != forTakers(entriesOf(batch, isGraded)).filterValues { it.isNotBlank() }
}

/** Which batch on-screen marks belong to: class, subject, test (exam component) and session. */
data class BatchKey(val cls: String, val subjectId: Long, val componentId: Long, val session: String)

class MarksEntryViewModel(
    private val studentRepo: StudentRepository,
    private val marksRepo: MarksRepository,
    private val sessionRepo: SessionRepository,
    private val metaRepo: MetaRepository,
    /** Classes to offer: every class for admins, else the staff member's own (possibly none). */
    classOptions: List<String>,
    isSuperAdmin: Boolean = false,
) : ViewModel() {

    private val _state = MutableStateFlow(
        MarksUiState(classOptions = classOptions, isSuperAdmin = isSuperAdmin)
    )
    val state: StateFlow<MarksUiState> = _state.asStateFlow()

    /** True once the teacher picks or types a session; the server default no longer overrides it. */
    private var sessionTouched = false
    private var batchJob: Job? = null
    private var subjectsJob: Job? = null
    private var rosterJob: Job? = null
    private var componentsJob: Job? = null

    private fun set(block: (MarksUiState) -> MarksUiState) { _state.value = block(_state.value) }

    init {
        viewModelScope.launch {
            val choice = sessionRepo.choice()
            set { it.copy(sessionOptions = if (choice.fromServer) choice.names else emptyList()) }
            // A late answer never wipes typed marks: the teacher keeps the session they began with.
            if (!sessionTouched && !_state.value.dirty && choice.current != _state.value.session) {
                changeSelection { it.copy(session = choice.current) }
                loadBatch()     // no-op until class, subject and test are picked
            }
        }
        viewModelScope.launch {
            val letters = metaRepo.gradeLetters()
            set { it.copy(gradeLetters = letters) }
        }
    }

    /**
     * Apply a change of class, subject, test or session. The marks and batch on screen
     * belonged to the old selection, so they go, and a batch load still running for it
     * is cancelled: the new selection's saved marks must load before anything is saved.
     */
    private fun changeSelection(block: (MarksUiState) -> MarksUiState) {
        batchJob?.cancel()
        set {
            block(it).copy(
                marks = emptyMap(), batch = null, loadedKey = null,
                loadingBatch = false, batchLoadFailed = false, message = null
            )
        }
    }

    fun setClass(c: String) {
        componentsJob?.cancel()
        changeSelection {
            it.copy(
                cls = c, subjects = emptyList(), subject = null,
                components = emptyList(), component = null,
                students = emptyList(), error = null
            )
        }
        subjectsJob?.cancel()
        subjectsJob = viewModelScope.launch {
            try {
                val subs = marksRepo.subjects(c)
                // A slow answer for a class the teacher has already left must not land.
                set { if (it.cls != c) it else it.copy(subjects = subs) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set { if (it.cls != c) it else it.copy(error = e.message ?: "Failed to load subjects") }
            }
        }
        loadRoster(c)
    }

    private fun loadRoster(c: String) {
        rosterJob?.cancel()
        set { it.copy(loadingRoster = true) }
        rosterJob = viewModelScope.launch {
            try {
                val roster = studentRepo.byClass(c).sortedWith(rosterOrder)
                // Another class's roster would put its students' marks in this class's batch.
                set { if (it.cls != c) it else it.copy(loadingRoster = false, students = roster) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set { if (it.cls != c) it else it.copy(loadingRoster = false, error = e.message ?: "Failed to load students") }
            }
        }
    }

    fun setSubject(s: ClassSubjectDto) {
        changeSelection { it.copy(subject = s, components = emptyList(), component = null) }
        componentsJob?.cancel()
        componentsJob = viewModelScope.launch {
            try {
                val detail = marksRepo.subjectDetail(s.id)
                set {
                    if (it.subject?.id != s.id) it
                    // Who takes it as of now, too: the class's subject list may be older.
                    else withTakers(it, s.id, detail.isOptional, detail.enrolledStudentIds)
                        .copy(components = detail.components.sortedBy { c -> c.orderIndex })
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set { if (it.subject?.id != s.id) it else it.copy(error = e.message ?: "Failed to load test types") }
            }
        }
    }

    fun setComponent(c: ExamComponentDto) {
        // Numeric digits and letters don't mix, and one test's marks must never be saved as another's.
        changeSelection { it.copy(component = c) }
        loadBatch()
    }

    /**
     * Typed session (free-text field: offline or an older server). The marks on screen
     * were the old session's, so they go; the screen offers "Load marks" for the new one.
     */
    fun setSession(value: String) {
        sessionTouched = true
        if (value == _state.value.session) return
        changeSelection { it.copy(session = value) }
    }

    /** Session picked from the server's list: reload the batch for it. */
    fun pickSession(value: String) {
        sessionTouched = true
        if (value == _state.value.session) return
        changeSelection { it.copy(session = value) }
        loadBatch()
    }

    /** (Re)load the saved batch for the current selection; also the screen's Load / Retry action. */
    fun loadBatch() {
        val s = _state.value
        val key = s.key ?: return
        val subject = s.subject ?: return
        val component = s.component ?: return
        batchJob?.cancel()
        set { it.copy(loadingBatch = true, batchLoadFailed = false, error = null, message = null) }
        batchJob = viewModelScope.launch {
            try {
                val batch = marksRepo.getBatch(key.cls, subject.subjectName, component.componentName, key.session)
                // A saved batch follows Class Subjects' max for its test. Another max means the
                // tests changed after the subject was picked: fetch them again, so the max
                // shown, checked and sent is the current one.
                val detail = if (batch != null && batch.maxMarks != component.maxMarks) subjectDetailOrNull(subject.id) else null
                set {
                    if (it.key != key) it
                    else {
                        // A removed test is reported by the save instead.
                        val fresh = detail?.let { d -> withTests(it, d) }?.takeIf { t -> t.component != null } ?: it
                        fresh.copy(loadingBatch = false, batch = batch, marks = entriesOf(batch, fresh.isGraded), loadedKey = key)
                    }
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                // Nothing is known about what's saved, so saving stays blocked until a retry
                // loads it: a save from an empty roster would delete every saved row.
                set {
                    if (it.key != key) it
                    else it.copy(
                        loadingBatch = false, batchLoadFailed = true, loadedKey = null,
                        error = e.message ?: "Failed to load marks"
                    )
                }
            }
        }
    }

    fun setMark(studentId: Long, value: String) {
        if (!_state.value.canEdit) return
        val digits = value.filter { it.isDigit() }.take(MAX_MARK_DIGITS)
        set { it.copy(marks = it.marks + (studentId to digits), message = null) }
    }

    /** Pick (or clear, with null) a graded exam's letter for one student. */
    fun setGrade(studentId: Long, letter: String?) {
        if (!_state.value.canEdit) return
        set { it.copy(marks = it.marks + (studentId to letter.orEmpty()), message = null) }
    }

    private fun buildBody(s: MarksUiState): BatchSaveBody {
        val items = s.entries.filter { it.value.isNotBlank() }.mapNotNull { (id, v) ->
            if (s.isGraded) MarkItemIn(studentId = id, grade = v)
            else v.toIntOrNull()?.let { MarkItemIn(studentId = id, marks = it) }
        }
        return BatchSaveBody(
            className = s.cls!!, subject = s.subject!!.subjectName,
            examType = s.component!!.componentName, session = s.session,
            maxMarks = s.maxMarks, items = items,
            // Only reached once this selection's batch has loaded (canSave), so this is it:
            // as loaded, or as the last save returned it.
            baseBatchId = s.batch?.id ?: 0L,
            baseRevision = s.batch?.revision,
        )
    }

    /** Save the on-screen marks: a draft, or (super-admin) changes to a submitted batch. */
    fun saveDraft() {
        val s = _state.value
        if (!s.canSave) return
        val key = s.key ?: return
        val body = buildBody(s)
        val wasLocked = s.locked
        set { it.copy(busy = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                if (takersChanged(key, s.subject)) return@launch
                val saved = marksRepo.saveBatch(body)
                applySaved(key, saved, if (wasLocked) "Changes saved (marks stay submitted)" else "Draft saved")
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                when {
                    e.testsChanged() -> afterTestsChanged(key, e, "Save failed")
                    e.notTaken() -> afterTakersRefused(key, e, "Save failed")
                    else -> set { failedSave(it, key, e, "Save failed") }
                }
            }
        }
    }

    fun submit() {
        val s = _state.value
        if (!s.canSubmit) return
        val key = s.key ?: return
        val body = buildBody(s)
        set { it.copy(busy = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                if (takersChanged(key, s.subject)) return@launch
                val saved = marksRepo.saveBatch(body)   // capture latest edits first
                // Keep the saved draft now: if the lock below fails, the next save or submit
                // must name this batch and its revision, not the copy the screen had before.
                set { if (it.key != key) it else it.copy(batch = saved, marks = entriesOf(saved, it.isGraded)) }
                val submitted = marksRepo.submit(saved.id)
                applySaved(key, submitted, "Marks submitted and locked")
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                when {
                    e.testsChanged() -> afterTestsChanged(key, e, "Submit failed")
                    e.notTaken() -> afterTakersRefused(key, e, "Submit failed")
                    else -> set { failedSave(it, key, e, "Submit failed") }
                }
            }
        }
    }

    fun requestEdit(reason: String) {
        val s = _state.value
        val batch = s.batch ?: return
        val key = s.key ?: return
        // A super-admin edits directly; the server answers 403 to their requests.
        if (s.isSuperAdmin || reason.isBlank() || !s.marksLoaded || s.busy) return
        set { it.copy(busy = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                marksRepo.requestEdit(batch.id, reason)
                // Reload to reflect the pending state.
                val refreshed = marksRepo.getBatch(
                    batch.className, batch.subject, batch.examType, batch.session
                )
                set {
                    if (it.key != key) it.copy(busy = false)
                    else it.copy(
                        busy = false, batch = refreshed,
                        message = "Edit request sent for super-admin approval"
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                set { it.copy(busy = false, error = e.message ?: "Request failed") }
            }
        }
    }

    /**
     * A refused save. A 409 means the saved marks changed after this screen loaded
     * them (another save, or the batch got locked): saving waits for a reload, which
     * brings back what is saved now.
     */
    private fun failedSave(s: MarksUiState, key: BatchKey, e: Exception, fallback: String): MarksUiState {
        val stale = (e as? ApiException)?.code == 409 && s.key == key
        val msg = e.userMessage(fallback)
        return if (stale) s.copy(busy = false, error = msg, loadedKey = null, batchLoadFailed = false)
        else s.copy(busy = false, error = msg)
    }

    /**
     * A save refused because Class Subjects changed this test after the subject was
     * picked (see [testsChanged]). Fetch the tests again, so the max shown, checked and
     * sent is the current one, and say what changed. Typed marks stay when they can still
     * be saved; otherwise the saved marks must load again first.
     */
    private suspend fun afterTestsChanged(key: BatchKey, e: Exception, fallback: String) {
        val detail = subjectDetailOrNull(key.subjectId)
        set {
            val old = it.component
            if (it.key != key || old == null) return@set it.copy(busy = false)
            if (detail == null) return@set it.copy(busy = false, error = e.userMessage(fallback))
            val next = withTests(it, detail)
            val now = next.component
                ?: return@set next.copy(
                    busy = false, marks = emptyMap(), batch = null, loadedKey = null, batchLoadFailed = false,
                    error = "“${old.componentName}” is no longer a test of ${detail.subjectName} in Class Subjects. Pick the test again."
                )
            val changes = buildList {
                if (detail.subjectName != it.subject?.subjectName) add("the subject is now called “${detail.subjectName}”")
                if (now.componentName != old.componentName) add("the test is now called “${now.componentName}”")
                if (now.maxMarks != old.maxMarks) add(
                    when {
                        now.maxMarks == 0 -> "${now.componentName} now takes a letter grade"
                        old.maxMarks == 0 -> "${now.componentName} now takes marks out of ${now.maxMarks}"
                        else -> "max marks for ${now.componentName} are now ${now.maxMarks} (were ${old.maxMarks})"
                    }
                )
            }
            if (changes.isEmpty()) return@set next.copy(busy = false, error = e.userMessage(fallback))
            // The server moves a saved batch along with such a change (a save from before it
            // is refused), and digits and letters don't mix: load the saved marks again.
            val reload = it.batch != null || (now.maxMarks == 0) != (old.maxMarks == 0)
            next.copy(
                busy = false,
                loadedKey = if (reload) null else it.loadedKey,
                batchLoadFailed = false,
                error = "Class Subjects changed after this test was picked: " + changes.joinToString("; ") + ". " +
                    if (reload) "Load the marks again, check them, then save." else "Check the marks, then save again."
            )
        }
    }

    /**
     * Before saving an optional subject. A save carries only the students listed as taking
     * it, and the server removes the saved marks of any student taking it whom a save leaves
     * out; who takes it can change on the website while this screen is open. So ask who
     * takes it now: when that changed, show the current list instead of saving and return
     * true. A subject the screen has as taken by the whole class needs no check (marks for
     * a student who doesn't take it are refused, see [afterTakersRefused]).
     */
    private suspend fun takersChanged(key: BatchKey, subject: ClassSubjectDto?): Boolean {
        val sub = subject?.takeIf { it.id == key.subjectId && it.isOptional } ?: return false
        val now = marksRepo.enrollments(sub.id)
        if (now.isOptional && now.studentIds.toSet() == sub.enrolledStudentIds.toSet()) return false
        set {
            if (it.key != key) it.copy(busy = false)
            else withTakers(it, sub.id, now.isOptional, now.studentIds)
                .copy(busy = false, error = takersChangedMessage(sub.subjectName, now))
        }
        return true
    }

    /**
     * A save refused (422) because it carried marks for students who don't take an
     * optional subject (see [notTaken]). Ask who takes it now, so only they are listed
     * and sent; the marks typed for them stay.
     */
    private suspend fun afterTakersRefused(key: BatchKey, e: Exception, fallback: String) {
        val now = try {
            marksRepo.enrollments(key.subjectId)
        } catch (c: CancellationException) {
            throw c
        } catch (_: Exception) {
            null
        }
        set {
            val msg = e.userMessage(fallback)
            when {
                it.key != key -> it.copy(busy = false)
                now == null -> it.copy(busy = false, error = msg)
                else -> withTakers(it, key.subjectId, now.isOptional, now.studentIds).copy(
                    busy = false,
                    error = "$msg The list now shows only the students taking it. Check the marks, then save again.",
                )
            }
        }
    }

    private suspend fun subjectDetailOrNull(subjectId: Long): ClassSubjectDetailDto? = try {
        marksRepo.subjectDetail(subjectId)
    } catch (e: CancellationException) {
        throw e
    } catch (_: Exception) {
        null
    }

    /** Show a save's result, unless the selection changed while it was in flight (then only `busy` clears). */
    private fun applySaved(key: BatchKey, saved: BatchDetailDto, msg: String) {
        set {
            if (it.key != key) it.copy(busy = false)
            else it.copy(
                busy = false, batch = saved,
                marks = entriesOf(saved, it.isGraded),
                message = msg
            )
        }
    }

    private companion object {
        /** Sort by roll number numerically, then by name (mirrors the web). */
        val rosterOrder = Comparator<StudentDto> { a, b ->
            val ar = a.rollNo ?: ""; val br = b.rollNo ?: ""
            if (ar.isNotEmpty() || br.isNotEmpty()) {
                if (ar.isEmpty()) return@Comparator 1
                if (br.isEmpty()) return@Comparator -1
                val an = ar.toIntOrNull(); val bn = br.toIntOrNull()
                if (an != null && bn != null && an != bn) return@Comparator an - bn
                if (an == null || bn == null) {
                    val c = ar.compareTo(br); if (c != 0) return@Comparator c
                }
            }
            a.name.compareTo(b.name, ignoreCase = true)
        }
    }
}
