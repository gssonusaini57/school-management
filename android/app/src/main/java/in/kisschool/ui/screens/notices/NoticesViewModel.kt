package `in`.kisschool.ui.screens.notices

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.repo.Notice
import `in`.kisschool.data.repo.NoticeRepository
import `in`.kisschool.data.repo.userMessage
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class NoticesUiState(
    val loading: Boolean = true,
    /** Newest first. Kept on a failed refresh, so the error shows above the old list. */
    val notices: List<Notice> = emptyList(),
    val error: String? = null,
    /** The notice open in the bottom sheet, by id. */
    val openId: Long? = null,
)

/** The read-only notice board: loads GET /notices and tracks which notice is open. */
class NoticesViewModel(private val repo: NoticeRepository) : ViewModel() {

    private val _state = MutableStateFlow(NoticesUiState())
    val state: StateFlow<NoticesUiState> = _state.asStateFlow()

    private var loadJob: Job? = null

    init {
        load()
    }

    fun load() {
        loadJob?.cancel()
        _state.update { it.copy(loading = true, error = null) }
        loadJob = viewModelScope.launch {
            try {
                val list = repo.list()
                _state.update { s ->
                    s.copy(
                        loading = false,
                        notices = list,
                        // A notice deleted on the web since it was opened closes its sheet.
                        openId = s.openId?.takeIf { id -> list.any { it.id == id } },
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.update { it.copy(loading = false, error = e.userMessage("Couldn't load notices")) }
            }
        }
    }

    fun open(id: Long) = _state.update { it.copy(openId = id) }

    fun close() = _state.update { it.copy(openId = null) }
}
