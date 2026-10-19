package `in`.kisschool

import android.content.res.Configuration
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.Drawable
import android.os.Bundle
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.ui.lock.BiometricGate
import `in`.kisschool.ui.nav.AppRoot
import `in`.kisschool.ui.theme.DarkBackground
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.StatusBarBackdrop
import `in`.kisschool.ui.update.UpdateGate

/**
 * The app's single activity. A [FragmentActivity] (still a ComponentActivity, so Compose's
 * setContent works as before) because androidx.biometric hosts the fingerprint / face / PIN
 * prompt of the app lock in a fragment.
 */
class MainActivity : FragmentActivity() {

    /** The XML theme's light window background, put back when the app returns to light. */
    private val lightWindowBackground: Drawable? by lazy {
        val attrs = theme.obtainStyledAttributes(intArrayOf(android.R.attr.windowBackground))
        try {
            attrs.getDrawable(0)
        } finally {
            attrs.recycle()
        }
    }

    /** Whether [applyWindowTheme] has swapped in the dark window background. */
    private var windowIsDark = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val container = (application as KisApp).container
        val settings = container.settings
        // Created here, with the activity: the unlock prompt for the lock screen, the saved
        // accounts on the login screen and the App lock switch in Settings.
        val gate = BiometricGate(this)

        // The XML theme (and so the starting window) is light. Style the window from the
        // saved choice before the first frame, so a Dark choice never shows a light window.
        applyWindowTheme(settings.themeMode.value.isDark(systemIsDark = isSystemNightMode()))

        setContent {
            val themeMode by settings.themeMode.collectAsStateWithLifecycle()
            val dark = themeMode.isDark(systemIsDark = isSystemInDarkTheme())
            // Home → Theme changes apply at once, no restart. (A phone dark-mode switch
            // recreates the activity, which lands in onCreate above.)
            DisposableEffect(dark) {
                applyWindowTheme(dark)
                onDispose { }
            }

            KISTheme(darkTheme = dark) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    StatusBarBackdrop {
                        // Force-update gate wraps the whole app: a too-old build is
                        // blocked by a non-dismissable overlay until it's updated.
                        UpdateGate(repo = container.appUpdateRepo) {
                            // The app behind its lock: start route, NavHost, the fingerprint /
                            // face / PIN gate, and the way back to Login when a session ends.
                            AppRoot(container = container, gate = gate, onExit = ::finish)
                        }
                    }
                }
            }
        }
    }

    private fun isSystemNightMode(): Boolean =
        (resources.configuration.uiMode and Configuration.UI_MODE_NIGHT_MASK) ==
            Configuration.UI_MODE_NIGHT_YES

    private fun applyWindowTheme(dark: Boolean) {
        enableEdgeToEdge(
            // White clock and icons in both themes: every screen has brand navy behind the
            // status bar (its top app bar, the login gradient, or StatusBarBackdrop).
            statusBarStyle = SystemBarStyle.dark(android.graphics.Color.TRANSPARENT),
            // Navigation-bar icons follow the chosen theme, not the phone's setting.
            navigationBarStyle = SystemBarStyle.auto(NAV_BAR_LIGHT_SCRIM, NAV_BAR_DARK_SCRIM) { dark },
        )
        if (dark != windowIsDark) {
            window.setBackgroundDrawable(
                if (dark) ColorDrawable(DarkBackground.toArgb()) else lightWindowBackground
            )
            windowIsDark = dark
        }
    }

    private companion object {
        // androidx.activity's own enableEdgeToEdge() defaults: the navigation-bar scrims used
        // where the system draws none itself (Android 8–9).
        val NAV_BAR_LIGHT_SCRIM = android.graphics.Color.argb(0xe6, 0xFF, 0xFF, 0xFF)
        val NAV_BAR_DARK_SCRIM = android.graphics.Color.argb(0x80, 0x1b, 0x1b, 0x1b)
    }
}
