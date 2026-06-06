package `in`.kisschool.ui.screens.studentdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.repo.StudentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StudentDetailUiState(
    val loading: Boolean = true,
    val student: StudentDto? = null,
    val error: String? = null,
    // Delete-request flow (mirrors the web "Request student deletion" dialog).
    val deleting: Boolean = false,
    val deleteError: String? = null,
    val deleteRequested: Boolean = false,  // success → screen pops back to the list
)

class StudentDetailViewModel(
    private val studentRepo: StudentRepository,
    private val studentId: Long,
    private val allowedClasses: List<String>
) : ViewModel() {

    private val _state = MutableStateFlow(StudentDetailUiState())
    val state: StateFlow<StudentDetailUiState> = _state.asStateFlow()

    init {
        load()
    }

    /** Re-fetch the student — called when returning from the edit screen so the
     *  pending-approval lock reflects a just-submitted edit. */
    fun reload() = load()

    /**
     * Request soft-deletion. Staff/admin edits are queued, so on success the
     * server returns the row as `pending_delete` and we flag [deleteRequested]
     * so the screen can pop back to the (refreshed) list.
     */
    fun requestDelete(reason: String?) {
        if (_state.value.deleting) return
        _state.value = _state.value.copy(deleting = true, deleteError = null)
        viewModelScope.launch {
            try {
                val updated = studentRepo.requestDelete(studentId, reason)
                _state.value = _state.value.copy(
                    deleting = false,
                    deleteRequested = true,
                    student = updated,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    deleting = false,
                    deleteError = e.message ?: "Delete request failed",
                )
            }
        }
    }

    fun clearDeleteError() {
        _state.value = _state.value.copy(deleteError = null)
    }

    /**
     * Fetch the single student via GET /students/{id} (staff-callable, class-scoped
     * server-side). This returns the full pending-edit metadata — crucially
     * `pendingEditRequestId` — which the list endpoint omits; without it the detail
     * screen never showed the "pending approval" banner / never disabled Edit.
     */
    private fun load() {
        viewModelScope.launch {
            try {
                val student = studentRepo.getStudent(studentId)
                _state.value = StudentDetailUiState(loading = false, student = student)
            } catch (e: Exception) {
                _state.value = StudentDetailUiState(
                    loading = false,
                    error = e.message ?: "Student not found"
                )
            }
        }
    }
}
