package `in`.kisschool.ui.screens.classestoday

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.ClassAttendanceRowDto
import `in`.kisschool.data.repo.DashboardRepository
import `in`.kisschool.data.repo.FeatureUnavailableException
import `in`.kisschool.data.repo.userMessage
import `in`.kisschool.ui.screens.dashboard.ClassDayKind
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import java.time.LocalDate

data class ClassesTodayUiState(
    val loading: Boolean = true,
    /** Every class in scope on the day, in school order; null until the first load answers. */
    val classes: List<ClassAttendanceRowDto>? = null,
    /** Kept with the old list on a failed refresh, so the error shows above it. */
    val error: String? = null,
    /** The server is older than the class summary. */
    val unavailable: String? = null,
)

/**
 * The marked, pending or holiday classes of one day ([kind], [date]), from the same class
 * summary the dashboard's rings are drawn from, fetched afresh here so the list is never
 * staler than the ring that opened it.
 */
class ClassesTodayViewModel(
    private val repo: DashboardRepository,
    val kind: ClassDayKind,
    val date: LocalDate,
) : ViewModel() {

    private val _state = MutableStateFlow(ClassesTodayUiState())
    val state: StateFlow<ClassesTodayUiState> = _state.asStateFlow()

    private var job: Job? = null

    init {
        load()
    }

    /** Fetch the day again (Refresh, Try again, back from saving a register). */
    fun load() {
        job?.cancel()
        _state.update { it.copy(loading = true, error = null) }
        job = viewModelScope.launch {
            try {
                val summary = repo.classSummary(date, date)
                _state.update { it.copy(loading = false, classes = summary.classes, unavailable = null) }
            } catch (e: CancellationException) {
                throw e
            } catch (e: FeatureUnavailableException) {
                _state.update { it.copy(loading = false, unavailable = e.message ?: "This server doesn't offer this yet.") }
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.userMessage("Couldn't load the classes")) }
            }
        }
    }
}
