package `in`.kisschool.ui.theme

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.statusBars
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.window.DialogWindowProvider
import androidx.core.view.WindowCompat

/**
 * Paints the brand navy behind the status bar, underneath [content]. The status-bar icons
 * are always white (MainActivity); most screens already put navy there (a top app bar, or
 * the login gradient, which draw over this strip), and this covers the ones that don't
 * (forgot / change password), so the clock never ends up white on white.
 * [content] gets the same constraints a Surface would give it.
 */
@Composable
fun StatusBarBackdrop(content: @Composable () -> Unit) {
    val statusBars = WindowInsets.statusBars
    val color = KISTheme.colors.topBar
    Box(
        Modifier
            .fillMaxSize()
            .drawBehind {
                drawRect(color, size = Size(size.width, statusBars.getTop(this).toFloat()))
            },
        propagateMinConstraints = true,
    ) {
        content()
    }
}

/**
 * Call inside a ModalBottomSheet's content. Material gives the sheet its own window and
 * sets that window's system-bar icons from the phone's dark-mode setting, not from the
 * app's theme choice; this makes them follow the app theme like the main window's
 * navigation bar. (Dark icons in the light theme are right here, unlike the main window:
 * a tall sheet rises under the status bar.)
 */
@Composable
fun SheetSystemBarsFollowAppTheme() {
    val view = LocalView.current
    val dark = MaterialTheme.colorScheme.surface.luminance() < 0.5f
    DisposableEffect(view, dark) {
        (view.parent as? DialogWindowProvider)?.window?.let { window ->
            WindowCompat.getInsetsController(window, window.decorView).apply {
                isAppearanceLightStatusBars = !dark
                isAppearanceLightNavigationBars = !dark
            }
        }
        onDispose { }
    }
}
