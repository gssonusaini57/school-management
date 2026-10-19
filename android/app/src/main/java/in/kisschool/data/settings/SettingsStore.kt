package `in`.kisschool.data.settings

import android.content.Context
import android.content.SharedPreferences
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

/** Which colours the app uses. Stored by [key], so renaming a constant never loses a choice. */
enum class ThemeMode(internal val key: String) {
    LIGHT("light"),
    DARK("dark"),
    /** Follow the phone's dark-mode setting. */
    SYSTEM("system");

    fun isDark(systemIsDark: Boolean): Boolean = when (this) {
        LIGHT -> false
        DARK -> true
        SYSTEM -> systemIsDark
    }

    companion object {
        /** Light is the school's approved look, so new installs and existing ones start there. */
        val DEFAULT = LIGHT

        fun fromKey(key: String?): ThemeMode = entries.firstOrNull { it.key == key } ?: DEFAULT
    }
}

/**
 * App settings in plain SharedPreferences: nothing here is secret (the session and the
 * saved accounts live in the encrypted [in.kisschool.data.auth.TokenStore] /
 * [in.kisschool.data.auth.AccountStore]). Each setting is a [StateFlow], so the UI applies
 * a change the moment it is made, without a restart.
 */
class SettingsStore(context: Context) {

    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFS_NAME, Context.MODE_PRIVATE)

    private val _themeMode = MutableStateFlow(ThemeMode.fromKey(prefs.getString(KEY_THEME_MODE, null)))
    val themeMode: StateFlow<ThemeMode> = _themeMode.asStateFlow()

    fun setThemeMode(mode: ThemeMode) {
        prefs.edit().putString(KEY_THEME_MODE, mode.key).apply()
        _themeMode.value = mode
    }

    /**
     * App lock: ask for the phone's fingerprint, face or PIN before showing a saved
     * sign-in (on a cold start, and again after 15 minutes in the background). One
     * switch for the whole phone; off until the person enables it from the popup after
     * a password sign-in or from Settings. Not a secret: it only says whether to ask.
     */
    private val _appLock = MutableStateFlow(prefs.getBoolean(KEY_APP_LOCK, false))
    val appLock: StateFlow<Boolean> = _appLock.asStateFlow()

    fun setAppLock(on: Boolean) {
        prefs.edit().putBoolean(KEY_APP_LOCK, on).apply()
        _appLock.value = on
    }

    private companion object {
        const val PREFS_NAME = "kis_settings"
        const val KEY_THEME_MODE = "theme_mode"
        const val KEY_APP_LOCK = "app_lock"
    }
}
