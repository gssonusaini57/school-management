package `in`.kisschool.ui.screens.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.repo.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

class ForgotPasswordViewModel(
    private val auth: AuthRepository,
) : ViewModel() {
    data class State(
        val loading: Boolean = false,
        val sent: Boolean = false,
        val error: String? = null,
    )

    private val _state = MutableStateFlow(State())
    val state: StateFlow<State> = _state.asStateFlow()

    fun submit(identifier: String) {
        val trimmed = identifier.trim()
        if (trimmed.isEmpty()) {
            _state.value = State(error = "Enter your email or phone")
            return
        }
        viewModelScope.launch {
            _state.value = State(loading = true)
            try {
                // Endpoint always returns a generic success — never reveals whether
                // the account exists, so we just flip to the "check your email" state.
                auth.forgotPassword(trimmed)
                _state.value = State(sent = true)
            } catch (e: Exception) {
                _state.value = State(error = e.message ?: "Something went wrong. Please try again.")
            }
        }
    }
}
