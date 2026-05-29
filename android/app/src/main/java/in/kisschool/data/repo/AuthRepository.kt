package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.ChangePasswordRequest
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

    /**
     * Returns true if the user must change their password before continuing.
     * When [remember] is true the identifier is persisted to prefill next time.
     */
    suspend fun login(identifier: String, password: String, remember: Boolean): Boolean {
        val resp = api.login(LoginRequest(identifier = identifier.trim(), password = password))
        tokenStore.saveSession(resp.token, resp.name, resp.allowedClasses, resp.forcePasswordChange)
        tokenStore.rememberedIdentifier = if (remember) identifier.trim() else null
        return resp.forcePasswordChange
    }

    suspend fun refreshMe() {
        val token = tokenStore.token ?: return
        val me = api.me()
        tokenStore.saveSession(token, me.name, me.allowedClasses, tokenStore.forcePasswordChange)
    }

    suspend fun changePassword(currentPassword: String, newPassword: String) {
        val resp = api.changeStaffPassword(ChangePasswordRequest(currentPassword, newPassword))
        if (!resp.isSuccessful) {
            throw RuntimeException(resp.errorBody()?.string() ?: "Password change failed (${resp.code()})")
        }
        tokenStore.setForcePasswordChange(false)
    }

    fun logout() = tokenStore.clear()
}
