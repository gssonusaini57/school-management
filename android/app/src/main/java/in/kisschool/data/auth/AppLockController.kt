package `in`.kisschool.data.auth

import android.os.SystemClock
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ProcessLifecycleOwner
import `in`.kisschool.data.settings.SettingsStore
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/**
 * Whether the app is behind its lock screen. Locks on a cold start when app lock is on and
 * an account is signed in, and again when the app comes back after [RELOCK_AFTER_MS] in the
 * background (the whole app, via [ProcessLifecycleOwner], not one activity). The lock
 * screen itself and the fingerprint / face / PIN prompt live in ui/lock; this only holds
 * the state. Must be created on the main thread (it registers a lifecycle observer).
 */
class AppLockController(
    private val settings: SettingsStore,
    private val accounts: AccountStore,
    private val tokenStore: TokenStore,
) : DefaultLifecycleObserver {

    private val _locked = MutableStateFlow(false)
    val locked: StateFlow<Boolean> = _locked.asStateFlow()

    private var backgroundedAt: Long? = null

    init {
        if (shouldLock()) _locked.value = true
        ProcessLifecycleOwner.get().lifecycle.addObserver(this)
    }

    /**
     * An active account that can open without a password: a stored or refreshable session.
     * The sign-in screens never have one (leaving the lock for them deactivates the
     * session, see AuthRepository.leaveSession), so the app never locks on top of them.
     */
    fun hasResumableSession(): Boolean {
        val active = accounts.active ?: return false
        return !tokenStore.token.isNullOrBlank() || !active.needsPassword
    }

    private fun shouldLock(): Boolean = settings.appLock.value && hasResumableSession()

    override fun onStop(owner: LifecycleOwner) {
        backgroundedAt = SystemClock.elapsedRealtime()
    }

    override fun onStart(owner: LifecycleOwner) {
        val since = backgroundedAt ?: return
        backgroundedAt = null
        if (!_locked.value && SystemClock.elapsedRealtime() - since >= RELOCK_AFTER_MS && shouldLock()) {
            _locked.value = true
        }
    }

    fun unlock() {
        _locked.value = false
    }

    companion object {
        const val RELOCK_AFTER_MS = 15 * 60 * 1000L
    }
}
