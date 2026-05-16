package com.expressonly.kisattendance.ui.screens.studentdetail

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.expressonly.kisattendance.data.api.dto.StudentDto
import com.expressonly.kisattendance.data.repo.StudentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class StudentDetailUiState(
    val loading: Boolean = true,
    val student: StudentDto? = null,
    val error: String? = null
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

    /**
     * The backend doesn't expose `GET /students/{id}` to staff (admins only); for staff we
     * fetch by class and find the student. Iterating only over the teacher's allowed classes
     * keeps the call count small (typically 1–3 classes).
     */
    private fun load() {
        viewModelScope.launch {
            try {
                for (cls in allowedClasses) {
                    val list = studentRepo.byClass(cls)
                    val match = list.firstOrNull { it.id == studentId }
                    if (match != null) {
                        _state.value = StudentDetailUiState(loading = false, student = match)
                        return@launch
                    }
                }
                _state.value = StudentDetailUiState(loading = false, error = "Student not found")
            } catch (e: Exception) {
                _state.value = StudentDetailUiState(
                    loading = false,
                    error = e.message ?: "Failed to load student"
                )
            }
        }
    }
}
