package com.expressonly.kisattendance.ui.screens.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.expressonly.kisattendance.data.api.dto.StudentDto
import com.expressonly.kisattendance.data.repo.AttendanceRepository
import com.expressonly.kisattendance.data.repo.StudentRepository
import com.expressonly.kisattendance.ui.components.todayIso
import kotlinx.coroutines.async
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class HistoryUiState(
    val allowedClasses: List<String> = emptyList(),
    val selectedClass: String? = null,
    val date: String = todayIso(),
    val students: List<StudentDto> = emptyList(),
    val statuses: Map<Long, String> = emptyMap(),
    val loading: Boolean = false,
    val error: String? = null,
    val noRecord: Boolean = false
)

class HistoryViewModel(
    private val studentRepo: StudentRepository,
    private val attendanceRepo: AttendanceRepository,
    allowedClasses: List<String>
) : ViewModel() {

    private val _state = MutableStateFlow(
        HistoryUiState(
            allowedClasses = allowedClasses,
            selectedClass = allowedClasses.firstOrNull()
        )
    )
    val state: StateFlow<HistoryUiState> = _state.asStateFlow()

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

    private fun reload() {
        val cls = _state.value.selectedClass ?: return
        val date = _state.value.date
        _state.value = _state.value.copy(loading = true, error = null, noRecord = false)
        viewModelScope.launch {
            try {
                val rosterDeferred = async { studentRepo.byClass(cls) }
                val attendanceDeferred = async { attendanceRepo.fetch(cls, date) }
                val roster = rosterDeferred.await()
                val attendance = attendanceDeferred.await()
                if (attendance == null) {
                    _state.value = _state.value.copy(
                        students = roster,
                        statuses = emptyMap(),
                        loading = false,
                        noRecord = true
                    )
                    return@launch
                }
                val statuses = attendance.records.mapKeys { it.key.toLong() }
                _state.value = _state.value.copy(
                    students = roster,
                    statuses = statuses,
                    loading = false,
                    noRecord = false
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: "Failed to load attendance"
                )
            }
        }
    }
}
