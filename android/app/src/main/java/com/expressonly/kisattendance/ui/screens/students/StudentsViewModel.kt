package com.expressonly.kisattendance.ui.screens.students

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.expressonly.kisattendance.data.api.dto.StudentDto
import com.expressonly.kisattendance.data.repo.StudentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StudentsUiState(
    val allowedClasses: List<String> = emptyList(),
    val selectedClass: String? = null,
    val students: List<StudentDto> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null
)

class StudentsViewModel(
    private val studentRepo: StudentRepository,
    allowedClasses: List<String>
) : ViewModel() {

    private val _state = MutableStateFlow(
        StudentsUiState(
            allowedClasses = allowedClasses,
            selectedClass = allowedClasses.firstOrNull()
        )
    )
    val state: StateFlow<StudentsUiState> = _state.asStateFlow()

    init {
        if (_state.value.selectedClass != null) reload()
    }

    fun selectClass(c: String) {
        _state.value = _state.value.copy(selectedClass = c)
        reload()
    }

    private fun reload() {
        val cls = _state.value.selectedClass ?: return
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val list = studentRepo.byClass(cls)
                _state.value = _state.value.copy(students = list, loading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: "Failed to load students"
                )
            }
        }
    }
}
