package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val identifier: String,
    val password: String
)

/*
 * `allowedMenus` (the staff member's menu grants, e.g. "marks-entry") is nullable on
 * purpose. These classes have required fields, so Gson builds them without running
 * the Kotlin constructor, and a key the server leaves out comes back as null even
 * for a non-null type. null therefore means "the server didn't say"; an empty list
 * means "no menus". Admin and super-admin get [] and pass every check by role.
 */
data class LoginResponse(
    val token: String,
    val role: String,
    val name: String,
    @SerializedName("allowed_classes") val allowedClasses: List<String> = emptyList(),
    @SerializedName("allowed_menus") val allowedMenus: List<String>? = null,
    @SerializedName("force_password_change") val forcePasswordChange: Boolean = false
)

data class MeResponse(
    val role: String,
    val name: String,
    @SerializedName("allowed_classes") val allowedClasses: List<String> = emptyList(),
    @SerializedName("allowed_menus") val allowedMenus: List<String>? = null,
)

data class ChangePasswordRequest(
    @SerializedName("current_password") val currentPassword: String,
    @SerializedName("new_password") val newPassword: String
)

// Backend accepts the same email-or-phone identifier as /auth/login.
data class ForgotPasswordRequest(
    val identifier: String
)

data class MessageResponse(
    val message: String = ""
)
