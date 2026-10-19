package `in`.kisschool.data.repo

import `in`.kisschool.data.CLASSES
import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.ChangePasswordRequest
import `in`.kisschool.data.api.dto.ForgotPasswordRequest
import `in`.kisschool.data.api.dto.LoginRequest
import `in`.kisschool.data.auth.TokenStore

class AuthRepository(
    private val api: ApiService,
    private val tokenStore: TokenStore
) {
    val isLoggedIn: Boolean get() = !tokenStore.token.isNullOrBlank()
    val displayName: String? get() = tokenStore.name
    val allowedClasses: List<String> get() = tokenStore.allowedClasses
    val forcePasswordChange: Boolean get() = tokenStore.forcePasswordChange
    val rememberedIdentifier: String? get() = tokenStore.rememberedIdentifier
    val role: String? get() = tokenStore.role
    val isAdmin: Boolean get() = role == "admin" || role == "super_admin"
    val isSuperAdmin: Boolean get() = role == "super_admin"
    val allowedMenus: List<String>? get() = tokenStore.allowedMenus

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
     * True once a login or /auth/me has answered in this process. From then on, menus
     * that still aren't stored mean a server older than menu grants, not "not
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

    /**
     * Returns true if the user must change their password before continuing.
     * When [remember] is true the identifier is persisted to prefill next time.
     */
    suspend fun login(identifier: String, password: String, remember: Boolean): Boolean {
        val resp = api.login(LoginRequest(identifier = identifier.trim(), password = password))
        tokenStore.saveSession(
            resp.token, resp.name, resp.allowedClasses, resp.forcePasswordChange, resp.role,
            allowedMenus = resp.allowedMenus,
        )
        serverAnswered = true
        tokenStore.rememberedIdentifier = if (remember) identifier.trim() else null
        return resp.forcePasswordChange
    }

    suspend fun refreshMe() {
        val token = tokenStore.token ?: return
        val me = api.me()
        tokenStore.saveSession(
            token, me.name, me.allowedClasses, tokenStore.forcePasswordChange, me.role,
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

    fun logout() {
        serverAnswered = false
        tokenStore.clear()
    }
}

/** Menu permission keys from backend/app/permissions.py (mirrored in frontend/src/lib/menus.ts). */
object MenuKeys {
    const val MARKS_ENTRY = "marks-entry"
    const val MARKS_RESULTS = "marks-results"
}
