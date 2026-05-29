package `in`.kisschool.ui.screens.marks

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.BatchDetailDto
import `in`.kisschool.data.api.dto.BatchSaveBody
import `in`.kisschool.data.api.dto.ClassSubjectDto
import `in`.kisschool.data.api.dto.ExamComponentDto
import `in`.kisschool.data.api.dto.MarkItemIn
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.repo.MarksRepository
import `in`.kisschool.data.repo.StudentRepository
import `in`.kisschool.ui.screens.studentedit.CLASSES
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.util.Calendar

private fun defaultSession(): String {
    val y = Calendar.getInstance().get(Calendar.YEAR)
    return "$y-${((y + 1) % 100).toString().padStart(2, '0')}"
}

data class MarksUiState(
    val classOptions: List<String> = CLASSES,
    val cls: String? = null,
    val subjects: List<ClassSubjectDto> = emptyList(),
    val subject: ClassSubjectDto? = null,
    val components: List<ExamComponentDto> = emptyList(),
    val component: ExamComponentDto? = null,
    val session: String = defaultSession(),
    val students: List<StudentDto> = emptyList(),
    val marks: Map<Long, String> = emptyMap(),
    val batch: BatchDetailDto? = null,
    val loadingRoster: Boolean = false,
    val loadingBatch: Boolean = false,
    val busy: Boolean = false,
    val error: String? = null,
    val message: String? = null,
) {
    val maxMarks: Int get() = component?.maxMarks ?: 0
    val locked: Boolean get() = batch?.status == "submitted"          // staff app: no super-admin
    val pending: Boolean get() = batch?.pendingEditRequestId != null
    val editable: Boolean get() = !locked && !pending
    val overMaxCount: Int
        get() = marks.values.count { it.isNotBlank() && (it.toIntOrNull() ?: 0) > maxMarks }
    val ready: Boolean get() = cls != null && subject != null && component != null && session.isNotBlank()
    val canSave: Boolean get() = ready && editable && overMaxCount == 0 && !busy
}

class MarksEntryViewModel(
    private val studentRepo: StudentRepository,
    private val marksRepo: MarksRepository,
    allowedClasses: List<String>,
) : ViewModel() {

    private val _state = MutableStateFlow(
        MarksUiState(classOptions = allowedClasses.ifEmpty { CLASSES })
    )
    val state: StateFlow<MarksUiState> = _state.asStateFlow()

    private fun set(block: (MarksUiState) -> MarksUiState) { _state.value = block(_state.value) }

    fun setClass(c: String) {
        set {
            it.copy(
                cls = c, subjects = emptyList(), subject = null,
                components = emptyList(), component = null,
                students = emptyList(), marks = emptyMap(), batch = null,
                error = null, message = null
            )
        }
        viewModelScope.launch {
            try {
                val subs = marksRepo.subjects(c)
                set { it.copy(subjects = subs) }
            } catch (e: Exception) {
                set { it.copy(error = e.message ?: "Failed to load subjects") }
            }
        }
        loadRoster(c)
    }

    private fun loadRoster(c: String) {
        set { it.copy(loadingRoster = true) }
        viewModelScope.launch {
            try {
                val roster = studentRepo.byClass(c).sortedWith(rosterOrder)
                set { it.copy(loadingRoster = false, students = roster) }
            } catch (e: Exception) {
                set { it.copy(loadingRoster = false, error = e.message ?: "Failed to load students") }
            }
        }
    }

    fun setSubject(s: ClassSubjectDto) {
        set { it.copy(subject = s, components = emptyList(), component = null, batch = null, message = null) }
        viewModelScope.launch {
            try {
                val detail = marksRepo.subjectDetail(s.id)
                set { it.copy(components = detail.components.sortedBy { c -> c.orderIndex }) }
            } catch (e: Exception) {
                set { it.copy(error = e.message ?: "Failed to load test types") }
            }
        }
    }

    fun setComponent(c: ExamComponentDto) {
        set { it.copy(component = c, message = null) }
        loadBatch()
    }

    fun setSession(value: String) {
        set { it.copy(session = value, message = null) }
    }

    /** Explicitly (re)load the batch for the current selection. */
    fun loadBatch() {
        val s = _state.value
        if (s.cls == null || s.subject == null || s.component == null || s.session.isBlank()) return
        set { it.copy(loadingBatch = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                val batch = marksRepo.getBatch(
                    s.cls, s.subject.subjectName, s.component.componentName, s.session
                )
                val marks = batch?.items?.associate { it.studentId to it.marks.toString() } ?: emptyMap()
                set { it.copy(loadingBatch = false, batch = batch, marks = marks) }
            } catch (e: Exception) {
                set { it.copy(loadingBatch = false, error = e.message ?: "Failed to load marks") }
            }
        }
    }

    fun setMark(studentId: Long, value: String) {
        val digits = value.filter { it.isDigit() }
        set { it.copy(marks = it.marks.toMutableMap().apply { this[studentId] = digits }, message = null) }
    }

    private fun buildBody(): BatchSaveBody {
        val s = _state.value
        val items = s.marks.filter { it.value.isNotBlank() }
            .map { MarkItemIn(it.key, it.value.toInt()) }
        return BatchSaveBody(
            className = s.cls!!, subject = s.subject!!.subjectName,
            examType = s.component!!.componentName, session = s.session,
            maxMarks = s.maxMarks, items = items
        )
    }

    fun saveDraft() {
        val s = _state.value
        if (!s.canSave) return
        set { it.copy(busy = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                val saved = marksRepo.saveBatch(buildBody())
                applySaved(saved, "Draft saved")
            } catch (e: Exception) {
                set { it.copy(busy = false, error = e.message ?: "Save failed") }
            }
        }
    }

    fun submit() {
        val s = _state.value
        if (!s.canSave) return
        set { it.copy(busy = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                val saved = marksRepo.saveBatch(buildBody())   // capture latest edits first
                val submitted = marksRepo.submit(saved.id)
                applySaved(submitted, "Marks submitted and locked")
            } catch (e: Exception) {
                set { it.copy(busy = false, error = e.message ?: "Submit failed") }
            }
        }
    }

    fun requestEdit(reason: String) {
        val batch = _state.value.batch ?: return
        if (reason.isBlank()) return
        set { it.copy(busy = true, error = null, message = null) }
        viewModelScope.launch {
            try {
                marksRepo.requestEdit(batch.id, reason)
                // Reload to reflect the pending state.
                val refreshed = marksRepo.getBatch(
                    batch.className, batch.subject, batch.examType, batch.session
                )
                set {
                    it.copy(
                        busy = false, batch = refreshed,
                        message = "Edit request sent for super-admin approval"
                    )
                }
            } catch (e: Exception) {
                set { it.copy(busy = false, error = e.message ?: "Request failed") }
            }
        }
    }

    private fun applySaved(saved: BatchDetailDto, msg: String) {
        set {
            it.copy(
                busy = false, batch = saved,
                marks = saved.items.associate { row -> row.studentId to row.marks.toString() },
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
