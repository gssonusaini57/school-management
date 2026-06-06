package `in`.kisschool.ui.screens.approvals

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.DeletionRequestDto
import `in`.kisschool.data.api.dto.EditRequestDto
import `in`.kisschool.data.api.dto.MarksEditRequestDto
import `in`.kisschool.data.repo.AdminRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class ApprovalsUiState(
    val loading: Boolean = false,
    val edits: List<EditRequestDto> = emptyList(),          // pending only
    val marks: List<MarksEditRequestDto> = emptyList(),     // pending only
    val deletions: List<DeletionRequestDto> = emptyList(),  // pending_delete + deleted
    val error: String? = null,
    val actionError: String? = null,
    val busyId: String? = null,
)

/** Drives the super-admin approval portal (student edits, marks edits, deletions).
 *  All three list endpoints are super-admin-only; per-queue runCatching keeps one
 *  failing queue from blanking the others. */
class ApprovalsViewModel(private val adminRepo: AdminRepository) : ViewModel() {

    private val _state = MutableStateFlow(ApprovalsUiState())
    val state: StateFlow<ApprovalsUiState> = _state.asStateFlow()

    init { load() }

    fun load() {
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val edits = runCatching { adminRepo.editRequests() }.getOrDefault(emptyList())
                    .filter { it.status == "pending" }
                val marks = runCatching { adminRepo.marksEditRequests() }.getOrDefault(emptyList())
                    .filter { it.status == "pending" }
                val dels = runCatching { adminRepo.deletionRequests() }.getOrDefault(emptyList())
                _state.value = _state.value.copy(
                    loading = false, edits = edits, marks = marks, deletions = dels, busyId = null,
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(loading = false, error = e.message ?: "Failed to load")
            }
        }
    }

    private fun act(id: String, block: suspend () -> Unit) {
        if (_state.value.busyId != null) return
        _state.value = _state.value.copy(busyId = id, actionError = null)
        viewModelScope.launch {
            try {
                block()
                load()  // refresh queues + clears busyId
            } catch (e: Exception) {
                _state.value = _state.value.copy(busyId = null, actionError = e.message ?: "Action failed")
            }
        }
    }

    fun approveEdit(id: Long) = act("edit-$id") { adminRepo.approveEdit(id) }
    fun rejectEdit(id: Long, reason: String?) = act("edit-$id") { adminRepo.rejectEdit(id, reason) }
    fun approveMarks(id: Long) = act("marks-$id") { adminRepo.approveMarksEdit(id) }
    fun rejectMarks(id: Long, reason: String?) = act("marks-$id") { adminRepo.rejectMarksEdit(id, reason) }
    fun approveDeletion(kind: String, id: Long) = act("del-$kind-$id") { adminRepo.approveDeletion(kind, id) }
    fun restoreDeletion(kind: String, id: Long) = act("del-$kind-$id") { adminRepo.restoreDeletion(kind, id) }
    fun purgeDeletion(kind: String, id: Long) = act("del-$kind-$id") { adminRepo.purgeDeletion(kind, id) }

    fun clearActionError() { _state.value = _state.value.copy(actionError = null) }
}
