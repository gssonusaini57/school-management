package `in`.kisschool.ui.screens.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.auth.LoginHandoff
import `in`.kisschool.data.auth.SavedAccount
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.data.repo.apiError
import `in`.kisschool.data.repo.userMessage
import `in`.kisschool.data.settings.SettingsStore
import `in`.kisschool.ui.lock.BiometricGate
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class LoginUiState(
    val identifier: String = "",
    val password: String = "",
    val busy: Boolean = false,
    val error: String? = null,
    /** Why the person is here ("your sign-in has expired"), shown above the form. */
    val notice: String? = null,
    val success: Boolean = false,
    val forcePasswordChange: Boolean = false,
    /** Ask "Sign in faster next time?" before leaving the screen. */
    val offerBiometric: Boolean = false,
    /** The accounts saved on this phone, most recently used first. */
    val accounts: List<SavedAccount> = emptyList(),
    val activeIdentifier: String? = null,
    /** A saved account waiting for the unlock prompt (app lock is on). */
    val gateFor: SavedAccount? = null,
    /** The saved account being opened. */
    val busyIdentifier: String? = null,
    /** The saved account "Remove" is asking about. */
    val confirmRemove: SavedAccount? = null,
    /** Bumped when the password field should take focus (an identifier was just filled in). */
    val focusPassword: Int = 0,
)

class LoginViewModel(
    private val auth: AuthRepository,
    private val settings: SettingsStore,
    /** Whether the phone can run the fingerprint / face / PIN prompt. */
    private val canUseBiometrics: () -> Boolean,
    /** Prefill and notice from whoever sent the app here (taken once). */
    handoff: LoginHandoff.Data? = null,
) : ViewModel() {
    private val _state = MutableStateFlow(LoginUiState())
    val state: StateFlow<LoginUiState> = _state.asStateFlow()

    /** The account the biometric popup is about, until it is answered. */
    private var offerFor: SavedAccount? = null

    init {
        viewModelScope.launch {
            combine(auth.savedAccounts, auth.activeIdentifier) { accounts, active -> accounts to active }
                .collect { (accounts, active) ->
                    _state.update { it.copy(accounts = accounts, activeIdentifier = active) }
                }
        }
        val prefill = handoff?.identifier
            // No saved accounts to pick from: the last identifier typed, as before.
            ?: auth.rememberedIdentifier?.takeIf { auth.savedAccounts.value.isEmpty() }
        _state.update {
            it.copy(
                identifier = prefill.orEmpty(),
                notice = handoff?.notice,
                // Sent here for one account's password: the cursor waits in the password field.
                focusPassword = if (handoff?.identifier != null) 1 else 0,
            )
        }
    }

    fun setIdentifier(value: String) {
        _state.update { it.copy(identifier = value, error = null) }
    }

    fun setPassword(value: String) {
        _state.update { it.copy(password = value, error = null) }
    }

    /** Password sign-in. The server always remembers this phone (see AuthRepository.login). */
    fun submit() {
        val id = _state.value.identifier.trim()
        val pw = _state.value.password
        if (id.isBlank() || pw.isBlank()) {
            _state.update { it.copy(error = "Enter your email/phone and password") }
            return
        }
        if (_state.value.busy) return
        _state.update { it.copy(busy = true, error = null, notice = null) }
        viewModelScope.launch {
            try {
                val outcome = auth.login(id, pw)
                val account = outcome.account
                // Offer the phone's unlock once per account on this phone, when it can be
                // used and app lock isn't already on. Never on a server without device
                // sessions (no account): there would be nothing for the lock to open.
                val offer = account != null && !auth.wasBiometricOffered(account) &&
                    !settings.appLock.value && canUseBiometrics()
                offerFor = account?.takeIf { offer }
                _state.update {
                    it.copy(
                        busy = false,
                        password = "",
                        forcePasswordChange = outcome.mustChange,
                        offerBiometric = offer,
                        success = !offer,
                    )
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: HttpException) {
                _state.update { it.copy(busy = false, error = loginError(e)) }
            } catch (e: Exception) {
                _state.update {
                    it.copy(busy = false, error = e.userMessage("Network error. Please check your connection."))
                }
            }
        }
    }

    /** "Sign in faster next time?": Enable turns app lock on; either way the popup is not shown again. */
    fun answerBiometricOffer(enable: Boolean) {
        offerFor?.let(auth::markBiometricOffered)
        offerFor = null
        if (enable) settings.setAppLock(true)
        _state.update { it.copy(offerBiometric = false, success = true) }
    }

    /**
     * A saved account was tapped: one that needs its password fills the form; otherwise
     * the unlock prompt first when app lock is on, then its session is refreshed.
     */
    fun useAccount(account: SavedAccount) {
        if (_state.value.busy || _state.value.gateFor != null) return
        if (account.needsPassword) {
            prefill(account, notice = "Enter your password to sign in as ${account.name.ifBlank { account.identifier }}.")
            return
        }
        if (settings.appLock.value) {
            _state.update { it.copy(gateFor = account, error = null) }
            return
        }
        resume(account)
    }

    /** The screen put up the unlock prompt for [LoginUiState.gateFor]; its answer comes to [onGateResult]. */
    fun onGatePrompted() {
        _state.update { it.copy(gateFor = null) }
    }

    fun onGateResult(account: SavedAccount, result: BiometricGate.Result) {
        _state.update { it.copy(gateFor = null) }
        when (result) {
            BiometricGate.Result.Success -> resume(account)
            is BiometricGate.Result.Unavailable -> prefill(
                account,
                notice = "Fingerprint, face or PIN isn't available on this phone right now. Enter your password.",
            )
            is BiometricGate.Result.Dismissed -> result.message?.let { msg -> _state.update { it.copy(error = msg) } }
        }
    }

    private fun resume(account: SavedAccount) {
        _state.update { it.copy(busy = true, busyIdentifier = account.identifier, error = null, notice = null) }
        viewModelScope.launch {
            when (val outcome = auth.resume(account)) {
                is AuthRepository.ResumeOutcome.Ok -> _state.update {
                    it.copy(busy = false, busyIdentifier = null, success = true, forcePasswordChange = outcome.mustChange)
                }
                AuthRepository.ResumeOutcome.NeedsPassword -> {
                    _state.update { it.copy(busy = false, busyIdentifier = null) }
                    prefill(account, notice = LoginHandoff.EXPIRED_NOTICE)
                }
                is AuthRepository.ResumeOutcome.Failed -> _state.update {
                    it.copy(
                        busy = false,
                        busyIdentifier = null,
                        error = outcome.error.userMessage("Couldn't sign in. Please try again."),
                    )
                }
            }
        }
    }

    private fun prefill(account: SavedAccount, notice: String?) {
        _state.update {
            it.copy(
                identifier = account.identifier,
                password = "",
                notice = notice,
                error = null,
                focusPassword = it.focusPassword + 1,
            )
        }
    }

    fun askRemove(account: SavedAccount) {
        if (!_state.value.busy) _state.update { it.copy(confirmRemove = account) }
    }

    fun cancelRemove() {
        _state.update { it.copy(confirmRemove = null) }
    }

    /** Signs the account out of this phone (the server is told in the background) and forgets it. */
    fun confirmRemove() {
        val account = _state.value.confirmRemove ?: return
        auth.forgetAccount(account.identifier)
        _state.update {
            it.copy(
                confirmRemove = null,
                identifier = if (it.identifier == account.identifier) "" else it.identifier,
                notice = null,
            )
        }
    }

    /** The server's own words for a 429 (too many attempts) or 400; "Invalid credentials" for a 401. */
    private fun loginError(e: HttpException): String {
        if (e.code() == 401) return "Invalid credentials"
        val detail = e.response()?.apiError()?.message
        return detail ?: "Login failed (HTTP ${e.code()})"
    }
}
