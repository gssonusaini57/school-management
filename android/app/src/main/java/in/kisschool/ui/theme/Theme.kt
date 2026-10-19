package `in`.kisschool.ui.theme

import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.TopAppBarColors
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.staticCompositionLocalOf
import androidx.compose.ui.graphics.Color

// ── Material colour schemes ─────────────────────────────────────────────

/** Khalsa blue, the website's brand blue (--color-khalsa-blue): light primary and every top bar. */
private val Primary = Color(0xFF0E2F8E)
private val OnPrimary = Color(0xFFFFFFFF)
private val Secondary = Color(0xFF16C172)
private val Surface = Color(0xFFFFFFFF)
private val Background = Color(0xFFF8FAFC)

/** The school's approved look. Roles not named here are the Material 3 baseline. */
private val Light = lightColorScheme(
    primary = Primary,
    onPrimary = OnPrimary,
    secondary = Secondary,
    background = Background,
    surface = Surface
)

/** Dark-theme screen background; MainActivity paints the window with it as well. */
internal val DarkBackground = Color(0xFF0B1220)
private val DarkPrimary = Color(0xFF7CA3D9)

/**
 * Navy-tinted dark scheme. Primary is a light blue so text, buttons and focus rings drawn
 * in primary stay readable on dark surfaces (top bars use the brand khalsa blue instead,
 * see [KisColors.topBar]). The secondary, tertiary and error roles keep the Material 3
 * baseline dark tones: the light scheme uses the baseline light ones, so a banner keeps
 * its colour family in both themes.
 */
private val Dark = darkColorScheme(
    primary = DarkPrimary,
    onPrimary = Color(0xFF062144),
    primaryContainer = Color(0xFF1E3A64),
    onPrimaryContainer = Color(0xFFD6E3FF),
    inversePrimary = Primary,
    secondary = Color(0xFF63DB9E),
    onSecondary = Color(0xFF00391F),
    background = DarkBackground,
    onBackground = Color(0xFFE2E8F0),
    surface = Color(0xFF111A2C),
    onSurface = Color(0xFFE2E8F0),
    surfaceVariant = Color(0xFF334058),
    onSurfaceVariant = Color(0xFFB6C0CF),
    inverseSurface = Color(0xFFE2E8F0),
    inverseOnSurface = Color(0xFF1E293B),
    outline = Color(0xFF7D8AA0),
    outlineVariant = Color(0xFF3B475D),
    surfaceBright = Color(0xFF2A364D),
    surfaceDim = DarkBackground,
    surfaceContainerLowest = Color(0xFF070C17),
    surfaceContainerLow = Color(0xFF131C2E),
    surfaceContainer = Color(0xFF172133),
    surfaceContainerHigh = Color(0xFF1C273B),
    surfaceContainerHighest = Color(0xFF222E44),
)

// ── Module accents ──────────────────────────────────────────────────────

/**
 * The app's areas. Each has its own accent ([ModuleAccent]) so a card, a drawer item or a
 * screen title says at a glance which part of the school it belongs to.
 */
enum class KisModule { Attendance, Students, Marks, Results, Approvals, Notices, Fees, Staff }

/**
 * One module's colours, read with `KISTheme.colors.module(m)`.
 *
 * [fg] is the icon (and any accent text) colour, readable on the card surface in its theme.
 * [container] is [fg] at 12 % (light) / 18 % (dark): translucent on purpose, it is drawn over
 * the card surface as the 40.dp circle behind the icon. [strip] is the 4.dp rule on the
 * card's start edge; it is the same in both themes and never used for text.
 */
@Immutable
data class ModuleAccent(val fg: Color, val container: Color, val strip: Color)

private const val LIGHT_CONTAINER_ALPHA = 0.12f
private const val DARK_CONTAINER_ALPHA = 0.18f

/** Light fg, dark fg and strip per module. Royal gold (#F5C518) is a strip only in light. */
private val ModulePalette: Map<KisModule, Triple<Color, Color, Color>> = mapOf(
    KisModule.Attendance to Triple(Color(0xFF0E2F8E), Color(0xFF9DB9FF), Color(0xFF0E2F8E)),
    KisModule.Students to Triple(Color(0xFF0F766E), Color(0xFF5EEAD4), Color(0xFF0F766E)),
    KisModule.Marks to Triple(Color(0xFF6D28D9), Color(0xFFC4B5FD), Color(0xFF6D28D9)),
    KisModule.Results to Triple(Color(0xFF9A6B00), Color(0xFFF5C518), Color(0xFFF5C518)),
    KisModule.Approvals to Triple(Color(0xFFB91C1C), Color(0xFFF87171), Color(0xFFE11D2C)),
    KisModule.Notices to Triple(Color(0xFFB45309), Color(0xFFFBBF24), Color(0xFFB45309)),
    KisModule.Fees to Triple(Color(0xFF047857), Color(0xFF6EE7B7), Color(0xFF047857)),
    KisModule.Staff to Triple(Color(0xFF334155), Color(0xFFCBD5E1), Color(0xFF334155)),
)

private fun moduleAccents(dark: Boolean): Map<KisModule, ModuleAccent> =
    KisModule.entries.associateWith { m ->
        val (lightFg, darkFg, strip) = ModulePalette.getValue(m)
        val fg = if (dark) darkFg else lightFg
        ModuleAccent(
            fg = fg,
            container = fg.copy(alpha = if (dark) DARK_CONTAINER_ALPHA else LIGHT_CONTAINER_ALPHA),
            strip = strip,
        )
    }

// ── App colours Material has no role for ────────────────────────────────

/**
 * Brand and status colours, each with a light and a dark value. The light values are
 * exactly the colours the screens hard-coded before the dark theme came back, so the
 * light look is unchanged. Read them with `KISTheme.colors`.
 */
@Immutable
data class KisColors(
    /** Top app bars and the strip behind the status bar: khalsa blue under white text and icons. */
    val topBar: Color,
    val onTopBar: Color,
    /** Login backdrop, top-left to bottom-right (the web admin login's deep indigo → khalsa blue). */
    val loginGradientStart: Color,
    val loginGradientEnd: Color,
    /** "Khalsa International" and "SENIOR SECONDARY SCHOOL" on the login card. */
    val schoolName: Color,
    val schoolTagline: Color,
    /** Attendance statuses drawn as text, outlines or light tints on a surface. */
    val present: Color,
    val absent: Color,
    val leave: Color,
    val halfDay: Color,
    /** No saved status (the history list's "—"). */
    val noStatus: Color,
    /** Solid day cells and legend dots of the coverage calendar, under [onCalendarDay] numbers. */
    val calendarMarked: Color,
    val calendarMissed: Color,
    val calendarHoliday: Color,
    val onCalendarDay: Color,
    /** Amber notes: draft marks, exams still missing, a pending deletion. */
    val warning: Color,
    /** Approvals diff: the old value (struck through) and the new one. */
    val diffOld: Color,
    val diffNew: Color,
    /** Spinner inside a filled button while it is busy (and so disabled). */
    val buttonSpinner: Color,
    /**
     * Royal gold (--color-royal-gold): the rule under the brand headers and the role chip's
     * text. Only ever drawn on the dark brand gradient or as a rule, never as text on a light
     * surface.
     */
    val royalGold: Color,
    /** Deep indigo (--color-deep-indigo): the role chip's background, under [royalGold] text. */
    val deepIndigo: Color,
    /** Per-module accents; read one with [module]. */
    val moduleAccents: Map<KisModule, ModuleAccent>,
) {
    /** The accent of module [m]. */
    fun module(m: KisModule): ModuleAccent = moduleAccents.getValue(m)

    /**
     * Bar colour for a class's attendance percentage: 90 % and up [present], 75 % up to 90 %
     * [leave] (amber), under 75 % (the PSEB board-exam eligibility line) [absent], and
     * [noStatus] when nothing is marked yet (null). Donut segments use [present], [halfDay],
     * [leave] and [absent] directly.
     */
    fun attendanceBand(percent: Double?): Color = when {
        percent == null || percent.isNaN() -> noStatus
        percent >= 90.0 -> present
        percent >= 75.0 -> leave
        else -> absent
    }
}

private val RoyalGold = Color(0xFFF5C518)
private val DeepIndigo = Color(0xFF08205C)

private val LightKisColors = KisColors(
    topBar = Primary,
    onTopBar = OnPrimary,
    loginGradientStart = Color(0xFF08205C),
    loginGradientEnd = Color(0xFF0E2F8E),
    schoolName = Color(0xFF08205C),
    schoolTagline = Color(0xFF0E2F8E),
    present = Color(0xFF16A34A),
    absent = Color(0xFFDC2626),
    leave = Color(0xFFD97706),
    halfDay = Color(0xFF2563EB),
    noStatus = Color.Gray,
    calendarMarked = Color(0xFF16A34A),
    calendarMissed = Color(0xFFD97706),
    calendarHoliday = Color(0xFF2563EB),
    onCalendarDay = Color.White,
    warning = Color(0xFFD97706),
    diffOld = Color(0xFFB91C1C),
    diffNew = Color(0xFF15803D),
    buttonSpinner = OnPrimary,
    royalGold = RoyalGold,
    deepIndigo = DeepIndigo,
    moduleAccents = moduleAccents(dark = false),
)

/**
 * Status accents use lighter tones that read on dark surfaces (at least 5:1 on the dark
 * cards). Calendar fills go a shade deeper instead, so the white day numbers keep their
 * contrast. Top bars stay khalsa blue: the status-bar icons over them are always white.
 */
private val DarkKisColors = KisColors(
    topBar = Primary,
    onTopBar = OnPrimary,
    loginGradientStart = Color(0xFF050D24),
    loginGradientEnd = Color(0xFF0B225E),
    schoolName = Color(0xFFD6E2FF),
    schoolTagline = Color(0xFF9DB9FF),
    present = Color(0xFF4ADE80),
    absent = Color(0xFFF87171),
    leave = Color(0xFFFBBF24),
    halfDay = Color(0xFF60A5FA),
    noStatus = Color(0xFF94A3B8),
    calendarMarked = Color(0xFF15803D),
    calendarMissed = Color(0xFFB45309),
    calendarHoliday = Color(0xFF1D4ED8),
    onCalendarDay = Color.White,
    warning = Color(0xFFFBBF24),
    diffOld = Color(0xFFF87171),
    diffNew = Color(0xFF4ADE80),
    buttonSpinner = DarkPrimary,
    royalGold = RoyalGold,
    deepIndigo = DeepIndigo,
    moduleAccents = moduleAccents(dark = true),
)

private val LocalKisColors = staticCompositionLocalOf { LightKisColors }

/**
 * The app theme. Light unless the user picks Dark in Home → Theme, or picks "Same as
 * phone" while the phone is in dark mode (MainActivity decides [darkTheme]).
 */
@Composable
fun KISTheme(darkTheme: Boolean = false, content: @Composable () -> Unit) {
    CompositionLocalProvider(LocalKisColors provides if (darkTheme) DarkKisColors else LightKisColors) {
        MaterialTheme(colorScheme = if (darkTheme) Dark else Light, content = content)
    }
}

object KISTheme {
    /** The [KisColors] of the current theme. */
    val colors: KisColors
        @Composable @ReadOnlyComposable get() = LocalKisColors.current
}

/** Colours for every screen's top app bar: khalsa blue with a white title and icons, in both themes. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun kisTopAppBarColors(): TopAppBarColors = TopAppBarDefaults.topAppBarColors(
    containerColor = KISTheme.colors.topBar,
    titleContentColor = KISTheme.colors.onTopBar,
    navigationIconContentColor = KISTheme.colors.onTopBar,
    actionIconContentColor = KISTheme.colors.onTopBar,
)
