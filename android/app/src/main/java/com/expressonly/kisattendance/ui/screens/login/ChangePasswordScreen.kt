package com.expressonly.kisattendance.ui.screens.login

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import com.expressonly.kisattendance.data.repo.AuthRepository
import com.expressonly.kisattendance.ui.components.ErrorBanner
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import retrofit2.HttpException

data class ChangePasswordUiState(
    val current: String = "",
    val newPw: String = "",
    val confirm: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    val success: Boolean = false
)

class ChangePasswordViewModel(private val auth: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow(ChangePasswordUiState())
    val state: StateFlow<ChangePasswordUiState> = _state.asStateFlow()

    fun setCurrent(v: String) { _state.value = _state.value.copy(current = v, error = null) }
    fun setNew(v: String) { _state.value = _state.value.copy(newPw = v, error = null) }
    fun setConfirm(v: String) { _state.value = _state.value.copy(confirm = v, error = null) }

    fun submit() {
        val s = _state.value
        if (s.current.isBlank() || s.newPw.isBlank()) {
            _state.value = s.copy(error = "Fill all fields")
            return
        }
        if (s.newPw.length < 6) {
            _state.value = s.copy(error = "New password must be at least 6 characters")
            return
        }
        if (s.newPw != s.confirm) {
            _state.value = s.copy(error = "New password and confirmation don't match")
            return
        }
        _state.value = s.copy(busy = true, error = null)
        viewModelScope.launch {
            try {
                auth.changePassword(s.current, s.newPw)
                _state.value = s.copy(busy = false, success = true)
            } catch (e: HttpException) {
                val msg = if (e.code() == 400) "Current password incorrect" else "Failed (HTTP ${e.code()})"
                _state.value = s.copy(busy = false, error = msg)
            } catch (e: Exception) {
                _state.value = s.copy(busy = false, error = e.message ?: "Network error")
            }
        }
    }
}

@Composable
fun ChangePasswordScreen(vm: ChangePasswordViewModel, onDone: () -> Unit) {
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.success) {
        if (state.success) onDone()
    }

    Box(
        Modifier.fillMaxSize().padding(24.dp),
        contentAlignment = Alignment.Center
    ) {
        Card(
            modifier = Modifier.widthIn(max = 480.dp).fillMaxWidth().wrapContentHeight(),
            elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
        ) {
            Column(
                Modifier.padding(24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {
                Text(
                    "Change password",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )
                Text(
                    "You're using a temporary password. Set a new one to continue.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.fillMaxWidth(),
                    textAlign = TextAlign.Center
                )

                Spacer(Modifier.height(8.dp))

                OutlinedTextField(
                    value = state.current,
                    onValueChange = vm::setCurrent,
                    label = { Text("Current password") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = state.newPw,
                    onValueChange = vm::setNew,
                    label = { Text("New password (min 6 chars)") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = state.confirm,
                    onValueChange = vm::setConfirm,
                    label = { Text("Confirm new password") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth()
                )

                ErrorBanner(state.error)

                Button(
                    onClick = vm::submit,
                    enabled = !state.busy,
                    modifier = Modifier.fillMaxWidth().height(52.dp)
                ) {
                    if (state.busy) CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.height(20.dp))
                    else Text("Update password")
                }
            }
        }
    }
}
