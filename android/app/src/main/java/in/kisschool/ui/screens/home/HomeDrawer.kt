package `in`.kisschool.ui.screens.home

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.WindowInsetsSides
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.only
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.systemBars
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import `in`.kisschool.R
import `in`.kisschool.ui.components.BrandRule
import `in`.kisschool.ui.components.ModuleIconCircle
import `in`.kisschool.ui.components.RoleChip
import `in`.kisschool.ui.components.brandGradient
import `in`.kisschool.ui.components.roleLabel
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisIcons
import `in`.kisschool.ui.theme.KisModule
import `in`.kisschool.ui.theme.PlayfairDisplay

/**
 * Home's navigation drawer: a brand header (crest, school name, the user and their role),
 * then every screen the user may open, each with its module's icon circle, and the app
 * settings below a divider. Marks entry, Results and Approvals follow the same grants the
 * screens themselves check.
 */
@Composable
internal fun HomeDrawerContent(
    userName: String,
    role: String?,
    isSuperAdmin: Boolean,
    canMarksEntry: Boolean,
    canResults: Boolean,
    onDashboard: () -> Unit,
    onTakeAttendance: () -> Unit,
    onViewHistory: () -> Unit,
    onViewStudents: () -> Unit,
    onMarksEntry: () -> Unit,
    onResults: () -> Unit,
    onApprovals: () -> Unit,
    onNotices: () -> Unit,
    onTheme: () -> Unit,
    onAbout: () -> Unit,
    onLogout: () -> Unit,
) {
    // Only the start inset (a navigation bar on that side in landscape) pads the sheet: the
    // gradient header runs up under the status bar (whose icons are always white), and the
    // list pads itself above the navigation bar.
    ModalDrawerSheet(
        drawerContainerColor = MaterialTheme.colorScheme.surface,
        windowInsets = WindowInsets.systemBars.only(WindowInsetsSides.Start),
    ) {
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
        ) {
            DrawerHeader(userName = userName, role = role)
            Spacer(Modifier.height(8.dp))

            val brand = brandIconColors()
            DrawerItem("Dashboard", KisIcons.Dashboard, brand, selected = true, onClick = onDashboard)
            DrawerItem("Take attendance", KisIcons.TakeAttendance, moduleIconColors(KisModule.Attendance), onClick = onTakeAttendance)
            DrawerItem("Past attendance", KisIcons.PastAttendance, moduleIconColors(KisModule.Attendance), onClick = onViewHistory)
            DrawerItem("Students", KisIcons.Students, moduleIconColors(KisModule.Students), onClick = onViewStudents)
            if (canMarksEntry) {
                DrawerItem("Marks entry", KisIcons.MarksEntry, moduleIconColors(KisModule.Marks), onClick = onMarksEntry)
            }
            if (canResults) {
                DrawerItem(
                    "Results & report cards",
                    KisIcons.Results,
                    moduleIconColors(KisModule.Results),
                    onClick = onResults,
                )
            }
            if (isSuperAdmin) {
                DrawerItem("Approvals", KisIcons.Approvals, moduleIconColors(KisModule.Approvals), onClick = onApprovals)
            }
            DrawerItem("Notices", KisIcons.Notices, moduleIconColors(KisModule.Notices), onClick = onNotices)

            HorizontalDivider(Modifier.padding(horizontal = 28.dp, vertical = 8.dp))

            val neutral = neutralIconColors()
            DrawerItem("Theme", KisIcons.Theme, neutral, onClick = onTheme)
            DrawerItem("About", KisIcons.About, neutral, onClick = onAbout)
            DrawerItem("Logout", KisIcons.Logout, neutral, onClick = onLogout)

            Spacer(
                Modifier
                    .navigationBarsPadding()
                    .height(12.dp)
            )
        }
    }
}

/** Crest, "Khalsa International" in Playfair Display, the user's name and role chip, on the brand gradient. */
@Composable
private fun DrawerHeader(userName: String, role: String?) {
    val onBrand = KISTheme.colors.onTopBar
    Column(
        Modifier
            .fillMaxWidth()
            .background(brandGradient())
    ) {
        Column(
            Modifier
                .fillMaxWidth()
                .statusBarsPadding()
                .padding(start = 24.dp, end = 24.dp, top = 20.dp, bottom = 18.dp),
            verticalArrangement = Arrangement.spacedBy(6.dp),
        ) {
            // The crest is 5:4, so only its height is fixed (CLAUDE.md Gotcha #11).
            Image(
                painter = painterResource(R.drawable.crest_mark),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.height(52.dp),
            )
            Spacer(Modifier.height(4.dp))
            Text(
                "Khalsa International",
                fontFamily = PlayfairDisplay,
                fontWeight = FontWeight.Bold,
                style = MaterialTheme.typography.titleLarge,
                color = onBrand,
            )
            if (userName.isNotBlank()) {
                Text(
                    userName.trim(),
                    style = MaterialTheme.typography.bodyLarge,
                    color = onBrand.copy(alpha = 0.92f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            roleLabel(role)?.let { RoleChip(it, Modifier.padding(top = 2.dp)) }
        }
        BrandRule()
    }
}

/** An icon's colour and the circle behind it. */
private data class IconColors(val fg: Color, val container: Color)

@Composable
private fun moduleIconColors(module: KisModule): IconColors =
    KISTheme.colors.module(module).let { IconColors(it.fg, it.container) }

/** Dashboard is the app itself rather than a module: the theme's primary, tinted like a module. */
@Composable
private fun brandIconColors(): IconColors {
    val primary = MaterialTheme.colorScheme.primary
    val dark = MaterialTheme.colorScheme.surface.luminance() < 0.5f
    return IconColors(primary, primary.copy(alpha = if (dark) 0.18f else 0.12f))
}

/** Settings rows: quiet grey icons in a faint circle, so the screens above stand out. */
@Composable
private fun neutralIconColors(): IconColors {
    val fg = MaterialTheme.colorScheme.onSurfaceVariant
    return IconColors(fg, fg.copy(alpha = 0.10f))
}

@Composable
private fun DrawerItem(
    label: String,
    icon: ImageVector,
    colors: IconColors,
    selected: Boolean = false,
    onClick: () -> Unit,
) {
    val primary = MaterialTheme.colorScheme.primary
    NavigationDrawerItem(
        label = { Text(label, maxLines = 1, overflow = TextOverflow.Ellipsis) },
        selected = selected,
        onClick = onClick,
        icon = { ModuleIconCircle(icon = icon, fg = colors.fg, container = colors.container, size = 36.dp) },
        colors = NavigationDrawerItemDefaults.colors(
            selectedContainerColor = primary.copy(alpha = 0.10f),
            selectedTextColor = primary,
        ),
        modifier = Modifier.padding(NavigationDrawerItemDefaults.ItemPadding),
    )
}
