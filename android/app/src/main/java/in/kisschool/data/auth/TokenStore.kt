package `in`.kisschool.data.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * Persists the JWT and minimal user metadata (name, allowed_classes) inside an
 * EncryptedSharedPreferences so the token is protected at rest.
 */
class TokenStore(context: Context) {

    private val prefs: SharedPreferences = run {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "kis_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }

    fun saveSession(token: String, name: String, allowedClasses: List<String>, forcePasswordChange: Boolean = false) {
        prefs.edit()
            .putString(KEY_TOKEN, token)
            .putString(KEY_NAME, name)
            .putString(KEY_CLASSES, allowedClasses.joinToString("|"))
            .putBoolean(KEY_FORCE_PW, forcePasswordChange)
            .apply()
    }

    fun setForcePasswordChange(value: Boolean) {
        prefs.edit().putBoolean(KEY_FORCE_PW, value).apply()
    }

    val token: String? get() = prefs.getString(KEY_TOKEN, null)
    val name: String? get() = prefs.getString(KEY_NAME, null)
    val allowedClasses: List<String>
        get() = prefs.getString(KEY_CLASSES, null)
            ?.split("|")
            ?.filter { it.isNotBlank() }
            ?: emptyList()
    val forcePasswordChange: Boolean get() = prefs.getBoolean(KEY_FORCE_PW, false)

    /** "Remember me" identifier — survives logout so the login field can prefill. */
    var rememberedIdentifier: String?
        get() = prefs.getString(KEY_REMEMBER_ID, null)
        set(value) {
            prefs.edit().apply {
                if (value.isNullOrBlank()) remove(KEY_REMEMBER_ID) else putString(KEY_REMEMBER_ID, value)
            }.apply()
        }

    /** Clears the session but preserves the remembered identifier across logout. */
    fun clear() {
        val remembered = rememberedIdentifier
        prefs.edit().clear().apply()
        if (!remembered.isNullOrBlank()) rememberedIdentifier = remembered
    }

    private companion object {
        const val KEY_TOKEN = "token"
        const val KEY_NAME = "name"
        const val KEY_CLASSES = "allowed_classes"
        const val KEY_FORCE_PW = "force_password_change"
        const val KEY_REMEMBER_ID = "remembered_identifier"
    }
}
