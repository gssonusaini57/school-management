package `in`.kisschool.data.repo

import `in`.kisschool.data.CLASSES
import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.ChangePasswordRequest
import `in`.kisschool.data.api.dto.DeviceInfo
import `in`.kisschool.data.api.dto.DeviceSessionDto
import `in`.kisschool.data.api.dto.ForgotPasswordRequest
import `in`.kisschool.data.api.dto.LoginRequest
import `in`.kisschool.data.api.dto.LogoutRequest
import `in`.kisschool.data.auth.AccountStore
import `in`.kisschool.data.auth.Jwt
import `in`.kisschool.data.auth.SavedAccount
import `in`.kisschool.data.auth.SessionManager
import `in`.kisschool.data.auth.TokenStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import retrofit2.HttpException

/**
 * Sign-in state: the active session ([TokenStore]), the accounts saved on this phone
 * ([AccountStore]) and the refresh tokens that keep them signed in ([SessionManager]).
 */
class AuthRepository(
    private val api: ApiService,
    private val tokenStore: TokenStore,
    private val accounts: AccountStore,
    private val sessions: SessionManager,
    /** Fire-and-forget server calls that must outlive the screen that started them (logout). */
    private val appScope: CoroutineScope,
    /** What this phone calls itself to the server (manufacturer + model). */
    private val deviceName: String,
) {
    /** A session that can open: an access token, or an active account with a refresh token. */
    val isLoggedIn: Boolean
        get() = !tokenStore.token.isNullOrBlank() || accounts.active?.needsPassword == false
    val displayName: String? get() = tokenStore.name
    val allowedClasses: List<String> get() = tokenStore.allowedClasses
    val forcePasswordChange: Boolean get() = tokenStore.forcePasswordChange
    val rememberedIdentifier: String? get() = tokenStore.rememberedIdentifier
    val role: String? get() = tokenStore.role
    val isAdmin: Boolean get() = role == "admin" || role == "super_admin"
    val isSuperAdmin: Boolean get() = role == "super_admin"
    val allowedMenus: List<String>? get() = tokenStore.allowedMenus

    /** The accounts saved on this phone, most recently used first, and the active one. */
    val savedAccounts: StateFlow<List<SavedAccount>> get() = accounts.accounts
    val activeIdentifier: StateFlow<String?> get() = accounts.activeIdentifier
    val activeAccount: SavedAccount? get() = accounts.active

    /**
     * The classes every class picker offers this user: the dashboard, Take and Past
     * attendance, Students, Marks entry and Results. Admins and super-admins carry an
     * empty allowed_classes and see every class; a staff member sees their own, which may
     * be none (the screens then say "No classes assigned"), so emptiness alone can't tell
     * the two apart. A role not stored yet (an install that logged in before the app kept
     * it, until /auth/me fills it in) keeps the old any-empty-means-all rule.
     */
    val visibleClasses: List<String>
        get() = when {
            isAdmin -> CLASSES
            role == null -> allowedClasses.ifEmpty { CLASSES }
            else -> allowedClasses
        }

    /**
     * True once a login, a refresh or /auth/me has answered in this process. From then
     * on, menus that still aren't stored mean a server older than menu grants, not "not
     * refreshed yet".
     */
    @Volatile private var serverAnswered = false

    /**
     * Whether the signed-in user may open the menu [menuKey] (see [MenuKeys]).
     * Mirrors canAccessMenu in frontend/src/lib/auth.ts: admin and super-admin pass
     * every check; staff need the key in their allowed_menus. When no menus are
     * stored (an install that logged in before this app version kept them), the
     * answer waits for the server: denied until a login or /auth/me answers in this
     * process (Home refreshes /auth/me on every open), then allowed only if that
     * answer had no allowed_menus, i.e. a server older than menu grants. Denying
     * first matters because the server doesn't check the Marks entry grant itself.
     */
    fun canAccess(menuKey: String): Boolean {
        if (isAdmin) return true
        val menus = tokenStore.allowedMenus ?: return serverAnswered
        return menuKey in menus
    }

    /** A password sign-in: [account] is null on a server too old for device sessions. */
    data class LoginOutcome(val mustChange: Boolean, val account: SavedAccount?)

    /**
     * Sign in with a password. Always asks the server to remember this phone (a refresh
     * token in the body, this device named manufacturer + model). The account is saved,
     * replacing an older entry for the same person, and made active.
     */
    suspend fun login(identifier: String, password: String): LoginOutcome {
        val id = identifier.trim()
        val resp = api.login(
            LoginRequest(
                identifier = id,
                password = password,
                remember = true,
                device = DeviceInfo(name = deviceName, platform = "android"),
            )
        )
        serverAnswered = true
        tokenStore.rememberedIdentifier = id
        if (resp.refreshToken.isNullOrBlank()) {
            // A server without device sessions: exactly the old one-hour sign-in.
            withContext(Dispatchers.IO) { sessions.storeLegacySignIn(resp) }
            return LoginOutcome(resp.forcePasswordChange, account = null)
        }
        // This phone's earlier sessions of the same person are ended, not left dangling in
        // their list of signed-in devices.
        val sub = Jwt.claims(resp.token)?.sub
        val stale = accounts.accounts.value
            .filter { it.identifier == id || (sub != null && it.accountRef == sub) }
            .mapNotNull { it.refreshToken }
            .filter { it != resp.refreshToken }
        val account = withContext(Dispatchers.IO) { sessions.storeSignIn(id, resp) }
        stale.forEach(::revokeQuietly)
        return LoginOutcome(resp.forcePasswordChange, account)
    }

    sealed interface ResumeOutcome {
        data class Ok(val mustChange: Boolean) : ResumeOutcome
        /** The saved session no longer works: the account needs its password. */
        data object NeedsPassword : ResumeOutcome
        data class Failed(val error: Throwable) : ResumeOutcome
    }

    /** Open a saved account without a password: reuses the active session if it is still good. */
    suspend fun resume(account: SavedAccount): ResumeOutcome {
        if (account.identifier == accounts.activeIdentifier.value && !Jwt.isExpired(tokenStore.token)) {
            return ResumeOutcome.Ok(tokenStore.forcePasswordChange)
        }
        return sessions.refresh(account).toOutcome()
    }

    /** After the app lock opens: make sure the active account's session is usable. */
    suspend fun resumeActive(): ResumeOutcome = sessions.resumeActive().toOutcome()

    private fun SessionManager.RefreshResult.toOutcome(): ResumeOutcome = when (this) {
        is SessionManager.RefreshResult.Refreshed -> {
            serverAnswered = true
            ResumeOutcome.Ok(mustChange)
        }
        SessionManager.RefreshResult.NeedsPassword -> ResumeOutcome.NeedsPassword
        is SessionManager.RefreshResult.Failed -> ResumeOutcome.Failed(error)
        // Only when the account was removed while it refreshed: nothing to open.
        SessionManager.RefreshResult.Superseded ->
            ResumeOutcome.Failed(ApiException("That account was signed out on this phone."))
    }

    suspend fun refreshMe() {
        val sentWith = tokenStore.token ?: return
        val subject = Jwt.claims(sentWith)?.sub
        val me = api.me()
        // The call may have refreshed the session on the way (a new access token, kept as
        // is); but if the phone switched to another account meanwhile, this answer is about
        // the previous one and must not land on the new session.
        val current = tokenStore.token ?: return
        if (subject != null && Jwt.claims(current)?.sub != subject) return
        tokenStore.updateUser(
            me.name, me.allowedClasses, me.role,
            // A server that leaves allowed_menus out keeps whatever login stored.
            allowedMenus = me.allowedMenus ?: tokenStore.allowedMenus,
        )
        serverAnswered = true
    }

    suspend fun changePassword(currentPassword: String, newPassword: String) {
        val resp = api.changeStaffPassword(ChangePasswordRequest(currentPassword, newPassword))
        if (!resp.isSuccessful) {
            throw RuntimeException(resp.errorBody()?.string() ?: "Password change failed (${resp.code()})")
        }
        tokenStore.setForcePasswordChange(false)
    }

    suspend fun forgotPassword(identifier: String) {
        api.forgotPassword(ForgotPasswordRequest(identifier.trim()))
    }

    /**
     * Sign the current account out of this phone: the session is cleared and the account
     * leaves the saved list at once; the server is told in the background (a failure
     * there only leaves a session that expires on its own).
     */
    fun logout() {
        val active = sessions.endActiveSession {
            val active = accounts.active
            serverAnswered = false
            tokenStore.clear()
            if (active != null) {
                accounts.remove(active.identifier)
                forgetRememberedIdentifier(active.identifier)
            } else {
                accounts.setActive(null)
            }
            active
        }
        active?.refreshToken?.let(::revokeQuietly)
    }

    /** "Remove" on the login screen's saved list: same as [logout], for any saved account. */
    fun forgetAccount(identifier: String) {
        val account = sessions.endActiveSession {
            val account = accounts.find(identifier) ?: return@endActiveSession null
            if (accounts.activeIdentifier.value == identifier) {
                serverAnswered = false
                tokenStore.clear()
            }
            accounts.remove(identifier)
            forgetRememberedIdentifier(identifier)
            account
        } ?: return
        account.refreshToken?.let(::revokeQuietly)
    }

    /**
     * Step out of the active session on this phone only ("Switch account", or the lock
     * screen's ways round the unlock): the access token is dropped and no account is active,
     * but the account stays saved and signed in on the server, so tapping it on the login
     * screen (behind the app lock when it is on) opens it again without a password. Nothing
     * signed in is left lying around while the sign-in screens show.
     */
    fun leaveSession() {
        sessions.endActiveSession {
            serverAnswered = false
            tokenStore.clear()
            accounts.setActive(null)
        }
    }

    /** Whether the "Sign in faster next time?" popup was already shown for [account] on this phone. */
    fun wasBiometricOffered(account: SavedAccount): Boolean = accounts.wasBiometricOffered(account)

    fun markBiometricOffered(account: SavedAccount) = accounts.markBiometricOffered(account)

    /** The account's signed-in devices. Not on servers before device sessions. */
    suspend fun sessions(): List<DeviceSessionDto> = try {
        api.deviceSessions()
    } catch (e: HttpException) {
        if (e.code() == 404 || e.code() == 405) {
            throw FeatureUnavailableException("Signed-in devices aren't available on this server yet.")
        }
        throw e
    }

    /** Signs one of the account's devices out; one already gone (404) counts as done. */
    suspend fun endSession(id: Long) {
        val resp = api.endDeviceSession(id)
        if (!resp.isSuccessful && resp.code() != 404) {
            throw ApiException(
                resp.apiError().message ?: "Couldn't sign that device out (HTTP ${resp.code()})",
                resp.code(),
            )
        }
    }

    /** The authenticator's refresh was refused: the process starts over at the login screen. */
    internal fun onSessionLost() {
        serverAnswered = false
    }

    /** A removed account's identifier no longer prefills the sign-in form. */
    private fun forgetRememberedIdentifier(identifier: String) {
        if (tokenStore.rememberedIdentifier.equals(identifier, ignoreCase = true)) tokenStore.rememberedIdentifier = null
    }

    private fun revokeQuietly(refreshToken: String) {
        appScope.launch { runCatching { api.logout(LogoutRequest(refreshToken)) } }
    }
}

/** Menu permission keys from backend/app/permissions.py (mirrored in frontend/src/lib/menus.ts). */
object MenuKeys {
    const val MARKS_ENTRY = "marks-entry"
    const val MARKS_RESULTS = "marks-results"
}
