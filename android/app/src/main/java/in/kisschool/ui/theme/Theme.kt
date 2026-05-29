package `in`.kisschool.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
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

private val Dark = darkColorScheme(
    primary = Color(0xFF7CA3D9),
    onPrimary = Color(0xFF062144),
    secondary = Color(0xFF63DB9E),
    background = Color(0xFF0B1220),
    surface = Color(0xFF111A2C)
)

@Composable
fun KISTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) Dark else Light
    MaterialTheme(colorScheme = colors, content = content)
}
