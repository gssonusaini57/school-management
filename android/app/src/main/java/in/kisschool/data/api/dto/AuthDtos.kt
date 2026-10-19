package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/*
 * Every field of these classes has a default, so Kotlin gives each a no-arg constructor
 * and Gson uses it: a key the server leaves out keeps the default (a server older than
 * the field), instead of a null in a non-null type. Nullable fields stay null on purpose
 * for "the server didn't say" (see allowedMenus). Nulls are not serialised, so a request
 * field left null is simply absent from the JSON.
 */

/** What this phone calls itself: shown back in GET /auth/sessions and the web's device list. */
data class DeviceInfo(
    val name: String = "",
    /** "android" (this app) or "web". */
    val platform: String = "android",
)

data class LoginRequest(
    val identifier: String = "",
    val password: String = "",
    /** Open a device session (refresh token) so the sign-in outlives the one-hour access token. */
    val remember: Boolean = false,
    /** Ignored by the server unless [remember] is true. */
    val device: DeviceInfo? = null,
)

/*
 * `allowedMenus` (the staff member's menu grants, e.g. "marks-entry") is nullable on
 * purpose: null means "the server didn't say"; an empty list means "no menus". Admin
 * and super-admin get [] and pass every check by role.
 */
data class LoginResponse(
    val token: String = "",
    val role: String = "",
    val name: String = "",
    @SerializedName("allowed_classes") val allowedClasses: List<String> = emptyList(),
    @SerializedName("allowed_menus") val allowedMenus: List<String>? = null,
    @SerializedName("force_password_change") val forcePasswordChange: Boolean = false,
    /** The device-session row behind [token]; null for a sign-in without remember. */
    @SerializedName("session_id") val sessionId: Long? = null,
    /** With remember on Android: the single-use refresh token for POST /auth/refresh. */
    @SerializedName("refresh_token") val refreshToken: String? = null,
    /** When [refreshToken] stops working (naive UTC ISO date-time, no Z). */
    @SerializedName("refresh_expires_at") val refreshExpiresAt: String? = null,
)

data class MeResponse(
    val role: String = "",
    val name: String = "",
    @SerializedName("allowed_classes") val allowedClasses: List<String> = emptyList(),
    @SerializedName("allowed_menus") val allowedMenus: List<String>? = null,
)

/** POST /auth/refresh: the refresh token this phone holds; the server answers a [LoginResponse]. */
data class RefreshRequest(
    @SerializedName("refresh_token") val refreshToken: String? = null,
)

/** POST /auth/logout: ends the device session the refresh token belongs to. */
data class LogoutRequest(
    @SerializedName("refresh_token") val refreshToken: String? = null,
)

/** One signed-in device of the caller's account (GET /auth/sessions). */
data class DeviceSessionDto(
    val id: Long = 0,
    @SerializedName("device_name") val deviceName: String = "",
    /** "android" | "web". */
    val platform: String = "",
    /** When the device first signed in (naive UTC ISO). */
    @SerializedName("created_at") val createdAt: String? = null,
    /** The device's last refresh; null until its first one. */
    @SerializedName("last_used_at") val lastUsedAt: String? = null,
    /** The session the caller's own access token came from. */
    @SerializedName("is_current") val isCurrent: Boolean = false,
)

data class ChangePasswordRequest(
    @SerializedName("current_password") val currentPassword: String = "",
    @SerializedName("new_password") val newPassword: String = "",
)

// Backend accepts the same email-or-phone identifier as /auth/login.
data class ForgotPasswordRequest(
    val identifier: String = "",
)

data class MessageResponse(
    val message: String = "",
)
