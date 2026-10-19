package `in`.kisschool.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val Primary = Color(0xFF0F3460)
private val OnPrimary = Color(0xFFFFFFFF)
private val Secondary = Color(0xFF16C172)
private val Surface = Color(0xFFFFFFFF)
private val Background = Color(0xFFF8FAFC)

private val Light = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    secondary = Secondary,
    background = Background,
    surface = Surface
)

/**
 * The school's design is light only: the app ignores the phone's dark mode, so cards and
 * screens stay white and the brand blue stays readable (in dark mode it used to turn the
 * login card dark grey with dark-blue text on it).
 */
@Composable
fun KISTheme(content: @Composable () -> Unit) {
    MaterialTheme(colorScheme = Light, content = content)
}
