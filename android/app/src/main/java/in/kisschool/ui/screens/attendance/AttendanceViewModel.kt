package `in`.kisschool.ui.screens.attendance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.repo.AttendanceRepository
import `in`.kisschool.data.repo.StudentRepository
import `in`.kisschool.ui.components.todayIso
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class AttendanceUiState(
    val allowedClasses: List<String> = emptyList(),
    val selectedClass: String? = null,
    val date: String = todayIso(),
    val students: List<StudentDto> = emptyList(),
    val statuses: Map<Long, String> = emptyMap(),
    val loading: Boolean = false,
    val saving: Boolean = false,
    val error: String? = null,
    val savedAt: Long = 0L
)

class AttendanceViewModel(
    private val studentRepo: StudentRepository,
    private val attendanceRepo: AttendanceRepository,
    allowedClasses: List<String>,
    initialClass: String? = null,
    initialDate: String? = null,
) : ViewModel() {

    private val _state = MutableStateFlow(
        AttendanceUiState(
            allowedClasses = allowedClasses,
            // Seed from the dashboard tap-through when provided, else first class + today.
            selectedClass = initialClass?.takeIf { it.isNotBlank() } ?: allowedClasses.firstOrNull(),
            date = initialDate?.takeIf { it.isNotBlank() } ?: todayIso(),
        )
    )
    val state: StateFlow<AttendanceUiState> = _state.asStateFlow()

    init {
        if (_state.value.selectedClass != null) reload()
    }

    fun selectClass(c: String) {
        _state.value = _state.value.copy(selectedClass = c)
        reload()
    }

    fun selectDate(iso: String) {
        _state.value = _state.value.copy(date = iso)
        reload()
    }

    fun setStatus(studentId: Long, code: String) {
        val map = _state.value.statuses.toMutableMap()
        map[studentId] = code
        _state.value = _state.value.copy(statuses = map)
    }

    fun reload() {
        val cls = _state.value.selectedClass ?: return
        val date = _state.value.date
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val rosterDeferred = async { studentRepo.byClass(cls) }
                val attendanceDeferred = async { attendanceRepo.fetch(cls, date) }
                val roster = rosterDeferred.await()
                val attendance = attendanceDeferred.await()
                val existing = attendance?.records?.mapKeys { it.key.toLong() } ?: emptyMap()
                val statuses = roster.associate { s ->
                    s.id to (existing[s.id] ?: "P")
                }
                _state.value = _state.value.copy(
                    students = roster,
                    statuses = statuses,
                    loading = false
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: "Failed to load class data"
                )
            }
        }
    }

    fun save() {
        val s = _state.value
        val cls = s.selectedClass ?: return
        if (s.students.isEmpty()) return
        _state.value = s.copy(saving = true, error = null)
        viewModelScope.launch {
            try {
                attendanceRepo.save(cls, s.date, s.statuses)
                _state.value = _state.value.copy(saving = false, savedAt = System.currentTimeMillis())
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    saving = false,
                    error = e.message ?: "Save failed"
                )
            }
        }
    }
}
