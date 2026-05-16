package com.expressonly.kisattendance.data.repo

import com.expressonly.kisattendance.data.api.ApiService
import com.expressonly.kisattendance.data.api.dto.ChangePasswordRequest
import com.expressonly.kisattendance.data.api.dto.LoginRequest
import com.expressonly.kisattendance.data.auth.TokenStore

class AuthRepository(
    private val api: ApiService,
    private val tokenStore: TokenStore
) {
    val isLoggedIn: Boolean get() = !tokenStore.token.isNullOrBlank()
    val displayName: String? get() = tokenStore.name
    val allowedClasses: List<String> get() = tokenStore.allowedClasses
    val forcePasswordChange: Boolean get() = tokenStore.forcePasswordChange

    /** Returns true if the user must change their password before continuing. */
    suspend fun login(identifier: String, password: String): Boolean {
        val resp = api.login(LoginRequest(identifier = identifier.trim(), password = password))
        tokenStore.saveSession(resp.token, resp.name, resp.allowedClasses, resp.forcePasswordChange)
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
