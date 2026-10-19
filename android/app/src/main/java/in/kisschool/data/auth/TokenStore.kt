package `in`.kisschool.data.auth

import android.content.SharedPreferences

/**
 * Persists the active account's JWT and minimal user metadata (name, role,
 * allowed_classes, allowed_menus) inside the encrypted preferences opened by
 * [SecurePrefs], shared with [AccountStore]. Only its own keys are ever cleared,
 * so signing out never drops the accounts saved on the phone.
 */
class TokenStore(private val prefs: SharedPreferences) {

    /**
     * [allowedMenus] null means the server didn't send menu grants: the stored value
     * is removed and [allowedMenus] reads back as null ("unknown").
     */
    fun saveSession(
        token: String,
        name: String,
        allowedClasses: List<String>,
        forcePasswordChange: Boolean = false,
        role: String? = null,
        allowedMenus: List<String>? = null,
    ) {
        prefs.edit()
            .putString(KEY_TOKEN, token)
            .putString(KEY_NAME, name)
            .putString(KEY_CLASSES, allowedClasses.joinToString("|"))
            .putBoolean(KEY_FORCE_PW, forcePasswordChange)
            .putString(KEY_ROLE, role)
            .apply {
                if (allowedMenus == null) remove(KEY_MENUS)
                else putString(KEY_MENUS, allowedMenus.filter { it.isNotBlank() }.joinToString("|"))
            }
            .apply()
    }

    /**
     * Updates the user metadata (from GET /auth/me) and leaves the access token alone: the
     * call that fetched it may have refreshed the session on the way, and the token it was
     * sent with is then already replaced.
     */
    fun updateUser(name: String, allowedClasses: List<String>, role: String?, allowedMenus: List<String>?) {
        prefs.edit()
            .putString(KEY_NAME, name)
            .putString(KEY_CLASSES, allowedClasses.joinToString("|"))
            .putString(KEY_ROLE, role)
            .apply {
                if (allowedMenus == null) remove(KEY_MENUS)
                else putString(KEY_MENUS, allowedMenus.filter { it.isNotBlank() }.joinToString("|"))
            }
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
    val role: String? get() = prefs.getString(KEY_ROLE, null)

    /**
     * Menu keys granted to a staff member (e.g. "marks-entry"); an empty list means
     * none. null when unknown: an install that logged in before the app stored
     * menus, until the next /auth/me refresh fills them in.
     */
    val allowedMenus: List<String>?
        get() {
            if (!prefs.contains(KEY_MENUS)) return null
            return prefs.getString(KEY_MENUS, null)
                ?.split("|")
                ?.filter { it.isNotBlank() }
                ?: emptyList()
        }

    /** "Remember me" identifier — survives logout so the login field can prefill. */
    var rememberedIdentifier: String?
        get() = prefs.getString(KEY_REMEMBER_ID, null)
        set(value) {
            prefs.edit().apply {
                if (value.isNullOrBlank()) remove(KEY_REMEMBER_ID) else putString(KEY_REMEMBER_ID, value)
            }.apply()
        }

    /**
     * Clears the session: the token and the user metadata. The remembered identifier and
     * everything [AccountStore] keeps in the same file stay.
     */
    fun clear() {
        prefs.edit()
            .remove(KEY_TOKEN)
            .remove(KEY_NAME)
            .remove(KEY_CLASSES)
            .remove(KEY_FORCE_PW)
            .remove(KEY_ROLE)
            .remove(KEY_MENUS)
            .apply()
    }

    private companion object {
        const val KEY_TOKEN = "token"
        const val KEY_NAME = "name"
        const val KEY_CLASSES = "allowed_classes"
        const val KEY_FORCE_PW = "force_password_change"
        const val KEY_ROLE = "role"
        const val KEY_MENUS = "allowed_menus"
        const val KEY_REMEMBER_ID = "remembered_identifier"
    }
}
