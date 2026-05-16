package com.expressonly.kisattendance.ui.screens.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.expressonly.kisattendance.data.repo.AuthRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class LoginUiState(
    val identifier: String = "",
    val password: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val success: Boolean = false,
    val forcePasswordChange: Boolean = false
)

class LoginViewModel(private val auth: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    fun setIdentifier(value: String) {
        _state.value = _state.value.copy(identifier = value, error = null)
    }

    fun setPassword(value: String) {
        _state.value = _state.value.copy(password = value, error = null)
    }

    fun submit() {
        val id = _state.value.identifier.trim()
        val pw = _state.value.password
        if (id.isBlank() || pw.isBlank()) {
            _state.value = _state.value.copy(error = "Enter your email/phone and password")
            return
        }
        _state.value = _state.value.copy(busy = true, error = null)
        viewModelScope.launch {
            try {
                val mustChange = auth.login(id, pw)
                _state.value = _state.value.copy(
                    busy = false,
                    success = true,
                    forcePasswordChange = mustChange
                )
            } catch (e: HttpException) {
                val msg = if (e.code() == 401) "Invalid credentials"
                else "Login failed (HTTP ${e.code()})"
                _state.value = _state.value.copy(busy = false, error = msg)
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    busy = false,
                    error = "Network error. Please check your connection."
                )
            }
        }
    }
}
