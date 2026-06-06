package `in`.kisschool.ui.screens.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.repo.AttendanceRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.YearMonth

data class DashboardUiState(
    val allowedClasses: List<String> = emptyList(),
    val selectedClass: String? = null,
    val month: YearMonth = YearMonth.now(),
    /** ISO dates in the displayed month that have an attendance record. */
    val markedDates: Set<String> = emptySet(),
    val loading: Boolean = false,
    val error: String? = null,
)

/**
 * Drives the attendance-coverage calendar on the home dashboard. Loads one month
 * of marked dates per (class, month) from a single endpoint; the calendar derives
 * marked/missed/off/future per day client-side (see MonthCalendar + WorkingWeek).
 */
class DashboardViewModel(
    private val attendanceRepo: AttendanceRepository,
    allowedClasses: List<String>,
) : ViewModel() {

    private val _state = MutableStateFlow(
        DashboardUiState(
            allowedClasses = allowedClasses,
            selectedClass = allowedClasses.firstOrNull(),
        )
    )
    val state: StateFlow<DashboardUiState> = _state.asStateFlow()

    init {
        if (_state.value.selectedClass != null) load()
    }

    fun selectClass(c: String) {
        _state.value = _state.value.copy(selectedClass = c)
        load()
    }

    fun prevMonth() {
        _state.value = _state.value.copy(month = _state.value.month.minusMonths(1))
        load()
    }

    fun nextMonth() {
        _state.value = _state.value.copy(month = _state.value.month.plusMonths(1))
        load()
    }

    /** Re-fetch the displayed month (e.g. after marking attendance from a day tap). */
    fun reloadCurrentMonth() = load()

    private fun load() {
        val cls = _state.value.selectedClass ?: return
        val ym = _state.value.month
        val from = ym.atDay(1).toString()
        val to = ym.atEndOfMonth().toString()
        _state.value = _state.value.copy(loading = true, error = null)
        viewModelScope.launch {
            try {
                val dates = attendanceRepo.markedDates(cls, from, to)
                _state.value = _state.value.copy(markedDates = dates, loading = false)
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    error = e.message ?: "Couldn't load attendance summary",
                )
            }
        }
    }
}
