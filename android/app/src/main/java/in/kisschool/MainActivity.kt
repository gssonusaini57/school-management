package `in`.kisschool

import android.content.res.Configuration
import android.graphics.drawable.ColorDrawable
import android.graphics.drawable.Drawable
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.toArgb
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.rememberNavController
import `in`.kisschool.ui.nav.AppNav
import `in`.kisschool.ui.nav.Routes
import `in`.kisschool.ui.theme.DarkBackground
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.StatusBarBackdrop
import `in`.kisschool.ui.update.UpdateGate

class MainActivity : ComponentActivity() {

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
                            val nav = rememberNavController()
                            val startRoute = when {
                                !container.authRepo.isLoggedIn -> Routes.LOGIN
                                container.authRepo.forcePasswordChange -> Routes.CHANGE_PASSWORD
                                else -> Routes.HOME
                            }
                            AppNav(navController = nav, startRoute = startRoute, container = container)

                            LaunchedEffect(Unit) {
                                container.authExpired.collect {
                                    nav.navigate(Routes.LOGIN) {
                                        popUpTo(0) { inclusive = true }
                                        launchSingleTop = true
                                    }
                                }
                            }
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
