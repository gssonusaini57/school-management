package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

data class LoginRequest(
    val identifier: String,
    val password: String
)

data class LoginResponse(
    val token: String,
    val role: String,
    val name: String,
    @SerializedName("allowed_classes") val allowedClasses: List<String> = emptyList(),
    @SerializedName("force_password_change") val forcePasswordChange: Boolean = false
)

data class MeResponse(
    val role: String,
    val name: String,
    @SerializedName("allowed_classes") val allowedClasses: List<String> = emptyList()
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
