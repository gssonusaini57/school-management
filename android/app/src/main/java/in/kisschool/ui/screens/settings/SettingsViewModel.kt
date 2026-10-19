package `in`.kisschool.ui.screens.settings

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.data.api.dto.DeviceSessionDto
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.data.repo.FeatureUnavailableException
import `in`.kisschool.data.repo.userMessage
import `in`.kisschool.data.settings.SettingsStore
import `in`.kisschool.data.settings.ThemeMode
import `in`.kisschool.ui.lock.BiometricGate
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class SettingsUiState(
    /** GET /auth/sessions in flight. */
    val loadingDevices: Boolean = true,
    /** The account's live device sessions, newest first. Kept on a failed reload. */
    val devices: List<DeviceSessionDto> = emptyList(),
    /** The list answered at least once, so an empty one means "none", not "not yet". */
    val devicesLoaded: Boolean = false,
    val devicesError: String? = null,
    /** A server older than device sessions: the section says so instead of listing. */
    val devicesUnavailable: String? = null,
    /** The device "Sign out" is asking about. */
    val confirmSignOut: DeviceSessionDto? = null,
    /** The device being signed out. */
    val signingOutId: Long? = null,
    /** Why App lock didn't turn on (the prompt was cancelled, timed out, locked out). */
    val lockMessage: String? = null,
    /** This phone was signed out from the list: the screen goes to the login screen. */
    val signedOut: Boolean = false,
)

/**
 * Settings: the theme, the phone-wide app lock, and the account's signed-in devices
 * (GET /auth/sessions) with a sign-out per device (DELETE /auth/sessions/{id}).
 */
class SettingsViewModel(
    private val auth: AuthRepository,
    private val settings: SettingsStore,
) : ViewModel() {

    private val _state = MutableStateFlow(SettingsUiState())
    val state: StateFlow<SettingsUiState> = _state.asStateFlow()

    val themeMode: StateFlow<ThemeMode> = settings.themeMode
    val appLock: StateFlow<Boolean> = settings.appLock

    /** Shown under the unlock prompt's title. */
    val accountName: String
        get() = auth.displayName?.ifBlank { null } ?: auth.activeAccount?.identifier.orEmpty()

    private var loadJob: Job? = null

    init {
        loadDevices()
    }

    fun setThemeMode(mode: ThemeMode) = settings.setThemeMode(mode)

    /** Turning the lock off needs no unlock: it only makes the app ask less. */
    fun turnOffAppLock() {
        settings.setAppLock(false)
        _state.update { it.copy(lockMessage = null) }
    }

    /** The answer of the unlock prompt that turning App lock on asks for first. */
    fun onEnableResult(result: BiometricGate.Result) {
        when (result) {
            BiometricGate.Result.Success -> {
                settings.setAppLock(true)
                _state.update { it.copy(lockMessage = null) }
            }
            is BiometricGate.Result.Dismissed -> _state.update { it.copy(lockMessage = result.message) }
            is BiometricGate.Result.Unavailable -> _state.update {
                it.copy(lockMessage = result.message ?: "Fingerprint, face or screen lock isn't available on this phone.")
            }
        }
    }

    fun loadDevices() {
        loadJob?.cancel()
        _state.update { it.copy(loadingDevices = true, devicesError = null) }
        loadJob = viewModelScope.launch {
            try {
                val list = auth.sessions()
                _state.update {
                    it.copy(loadingDevices = false, devices = list, devicesLoaded = true, devicesUnavailable = null)
                }
            } catch (e: CancellationException) {
                throw e
            } catch (e: FeatureUnavailableException) {
                _state.update { it.copy(loadingDevices = false, devicesUnavailable = e.message) }
            } catch (e: Exception) {
                _state.update {
                    it.copy(loadingDevices = false, devicesError = e.userMessage("Couldn't load your signed-in devices"))
                }
            }
        }
    }

    fun askSignOut(device: DeviceSessionDto) {
        if (_state.value.signingOutId == null) _state.update { it.copy(confirmSignOut = device) }
    }

    fun cancelSignOut() {
        _state.update { it.copy(confirmSignOut = null) }
    }

    fun confirmSignOut() {
        val device = _state.value.confirmSignOut ?: return
        _state.update { it.copy(confirmSignOut = null) }
        if (device.isCurrent) {
            // This phone: the same as Logout (the server is told in the background).
            auth.logout()
            _state.update { it.copy(signedOut = true) }
            return
        }
        _state.update { it.copy(signingOutId = device.id, devicesError = null) }
        viewModelScope.launch {
            try {
                auth.endSession(device.id)
                _state.update { s -> s.copy(signingOutId = null, devices = s.devices.filterNot { it.id == device.id }) }
                loadDevices()
            } catch (e: CancellationException) {
                throw e
            } catch (e: Exception) {
                _state.update {
                    it.copy(signingOutId = null, devicesError = e.userMessage("Couldn't sign that device out"))
                }
            }
        }
    }
}
