package `in`.kisschool.ui.lock

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.kisschool.data.auth.LoginHandoff
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.di.AppContainer
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

/** How a lock ended; the app root acts on it once (see ui/nav/AppRoot.kt). */
sealed interface LockOutcome {
    /**
     * Unlocked, and the active session is usable: the access token was still good or was
     * refreshed (the new refresh token saved first). Also when the server couldn't be
     * reached: the unlock itself succeeded, each screen shows its own network error and the
     * next request refreshes again. [mustChange]: the refreshed session says the password
     * must be changed first.
     */
    data class Unlocked(val mustChange: Boolean) : LockOutcome

    /** To the login screen for [identifier]'s password, saying [notice] (null: nothing to say). */
    data class UsePassword(val identifier: String?, val notice: String?) : LockOutcome

    /** To the login screen's list of saved accounts. */
    data object SwitchAccount : LockOutcome
}

data class LockUiState(
    /**
     * The session is being refreshed after a successful unlock. Not set while the prompt
     * itself is up (it covers the screen anyway): a prompt that ever vanished without an
     * answer must not leave "Unlock" disabled for good.
     */
    val busy: Boolean = false,
    /** Why the last attempt didn't unlock (a lockout, a timeout); null when nothing to say. */
    val message: String? = null,
    val outcome: LockOutcome? = null,
)

/**
 * The lock screen's state. Scoped to the activity (it is created outside the NavHost), so a
 * prompt answered while the activity is being recreated (a rotation) still lands here; it
 * is reset after each lock, ready for the next one.
 */
class LockViewModel(private val auth: AuthRepository) : ViewModel() {
    private val _state = MutableStateFlow(LockUiState())
    val state: StateFlow<LockUiState> = _state.asStateFlow()

    fun onPromptShown() {
        _state.update { it.copy(message = null) }
    }

    fun onPromptResult(identifier: String?, result: BiometricGate.Result) {
        if (_state.value.busy) return
        when (result) {
            BiometricGate.Result.Success -> viewModelScope.launch {
                _state.update { it.copy(busy = true) }
                val outcome = when (val r = auth.resumeActive()) {
                    is AuthRepository.ResumeOutcome.Ok -> LockOutcome.Unlocked(r.mustChange)
                    // The server refused the saved sign-in: the account stays listed, but
                    // needs its password.
                    AuthRepository.ResumeOutcome.NeedsPassword ->
                        LockOutcome.UsePassword(identifier, LoginHandoff.EXPIRED_NOTICE)
                    is AuthRepository.ResumeOutcome.Failed -> LockOutcome.Unlocked(mustChange = false)
                }
                _state.update { it.copy(busy = false, outcome = outcome) }
            }
            // Nothing enrolled, no hardware, locked out for good: the password it is.
            is BiometricGate.Result.Unavailable -> _state.update {
                it.copy(busy = false, outcome = LockOutcome.UsePassword(identifier, UNAVAILABLE_NOTICE))
            }
            is BiometricGate.Result.Dismissed -> _state.update { it.copy(busy = false, message = result.message) }
        }
    }

    fun usePassword(identifier: String?) {
        if (!_state.value.busy) _state.update { it.copy(outcome = LockOutcome.UsePassword(identifier, null)) }
    }

    fun switchAccount() {
        if (!_state.value.busy) _state.update { it.copy(outcome = LockOutcome.SwitchAccount) }
    }

    /** The outcome was acted on: back to a fresh state for the next lock. */
    fun consumed() {
        _state.value = LockUiState()
    }

    companion object {
        const val UNAVAILABLE_NOTICE =
            "Fingerprint, face or PIN isn't available on this phone right now. Enter your password."
    }
}

/**
 * The app lock in action, composed over the app while [AppContainer.appLock] says locked:
 * puts up the unlock prompt as soon as it appears (a cold start, or back from the background
 * after 15 minutes) and again on "Unlock"; on success makes sure the active account's
 * session is usable (refreshing it when the access token has expired), then reports
 * [LockOutcome.Unlocked]. A refused refresh, a phone without a usable fingerprint, face or
 * PIN, "Use password" and "Switch account" report the way to the login screen instead.
 */
@Composable
fun LockGate(
    container: AppContainer,
    gate: BiometricGate,
    onOutcome: (LockOutcome) -> Unit,
    onBack: () -> Unit,
) {
    val vm: LockViewModel = viewModel { LockViewModel(container.authRepo) }
    val s by vm.state.collectAsStateWithLifecycle()
    // The account this lock protects; fixed for the life of the lock screen.
    val account = remember { container.accounts.active }
    // Saved across a rotation: the prompt comes up by itself once per lock, not once per
    // activity (a prompt already up survives the rotation and answers the same ViewModel).
    var autoPrompted by rememberSaveable { mutableStateOf(false) }

    fun prompt() {
        if (vm.state.value.busy) return
        vm.onPromptShown()
        gate.authenticate(subtitle = account?.name?.ifBlank { null } ?: account?.identifier.orEmpty()) { result ->
            vm.onPromptResult(account?.identifier, result)
        }
    }

    LaunchedEffect(Unit) {
        if (!autoPrompted) {
            autoPrompted = true
            prompt()
        }
    }

    LaunchedEffect(s.outcome) {
        val outcome = s.outcome ?: return@LaunchedEffect
        vm.consumed()
        onOutcome(outcome)
    }

    LockScreen(
        accountName = account?.name?.ifBlank { null } ?: account?.identifier.orEmpty(),
        message = s.message,
        busy = s.busy,
        onUnlock = ::prompt,
        onUsePassword = { vm.usePassword(account?.identifier) },
        onSwitchAccount = vm::switchAccount,
        onBack = onBack,
    )
}
