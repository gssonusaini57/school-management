package `in`.kisschool.ui.screens.home

import androidx.activity.compose.BackHandler
import android.widget.Toast
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Menu
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.BuildConfig
import `in`.kisschool.R
import `in`.kisschool.ui.components.BrandRule
import `in`.kisschool.ui.components.RoleChip
import `in`.kisschool.ui.components.brandGradient
import `in`.kisschool.ui.components.roleLabel
import `in`.kisschool.ui.screens.dashboard.ClassDayKind
import `in`.kisschool.ui.screens.dashboard.DashboardActions
import `in`.kisschool.ui.screens.dashboard.DashboardViewModel
import `in`.kisschool.ui.screens.dashboard.adminDashboard
import `in`.kisschool.ui.screens.dashboard.portalPageUrl
import `in`.kisschool.ui.screens.dashboard.teacherDashboard
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.PlayfairDisplay
import kotlinx.coroutines.launch
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * Home: a brand header, then the role's dashboard: the school-wide cards for admins and the
 * super-admin, the teacher's own classes for staff (see DashboardCards.kt). Every other screen
 * opens from the navigation drawer behind the top bar's menu button, or from a card.
 *
 * The body is a LazyColumn of cards: a new dashboard card is one more `cardItem(…)` in
 * adminDashboard / teacherDashboard, a DashboardCard with `Modifier.padding(horizontal = 16.dp)`.
 * The refresh button reloads every card; each card loads (and fails) on its own.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    userName: String,
    /** The stored role ("super_admin" | "admin" | "staff"), or null until /auth/me has said. */
    role: String?,
    dashVm: DashboardViewModel,
    onOpenAttendanceFor: (className: String, iso: String) -> Unit,
    /** The dashboard's lists of one day's marked / pending / holiday classes. */
    onOpenClassesToday: (kind: ClassDayKind, iso: String) -> Unit,
    onTakeAttendance: () -> Unit,
    onViewHistory: () -> Unit,
    onViewStudents: () -> Unit,
    /** Students, Marks entry and Results opened from a dashboard card, on a class when given. */
    onStudentsFor: (className: String?) -> Unit,
    onMarksEntry: () -> Unit,
    onMarksEntryFor: (className: String?) -> Unit,
    onResultsFor: (className: String?) -> Unit,
    onNotices: () -> Unit,
    onLogout: () -> Unit,
    isSuperAdmin: Boolean = false,
    onApprovals: () -> Unit = {},
    /** Staff need the "marks-entry" / "marks-results" menu grants; admins always see both. */
    canMarksEntry: Boolean = true,
    canResults: Boolean = true,
    onResults: () -> Unit = {},
    /** Drawer → Settings: theme, app lock and the account's signed-in devices. */
    onSettings: () -> Unit,
    /** Drawer → Switch account, shown for a sign-in saved on this phone. */
    canSwitchAccount: Boolean = false,
    onSwitchAccount: () -> Unit = {},
) {
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var showAbout by remember { mutableStateOf(false) }
    var confirmLogout by remember { mutableStateOf(false) }
    val s by dashVm.state.collectAsStateWithLifecycle()
    val cards by dashVm.cards.collectAsStateWithLifecycle()
    val uriHandler = LocalUriHandler.current
    val context = LocalContext.current
    val actions = DashboardActions(
        onOpenAttendanceFor = onOpenAttendanceFor,
        onOpenClasses = onOpenClassesToday,
        onApprovals = onApprovals,
        onResults = onResultsFor,
        onMarksEntry = onMarksEntryFor,
        onStudents = onStudentsFor,
        onNotices = onNotices,
        onOpenFees = {
            // Fees aren't in the app: the card opens the web portal's fees page.
            val url = portalPageUrl(BuildConfig.API_BASE_URL, "fees")
            try {
                uriHandler.openUri(url)
            } catch (_: Exception) {
                Toast.makeText(context, "No browser could open $url", Toast.LENGTH_LONG).show()
            }
        },
        onRetry = dashVm::retry,
        onSelectPeriod = dashVm::selectPeriod,
        onToggleClass = dashVm::toggleClass,
        onPrevMonth = dashVm::prevMonth,
        onNextMonth = dashVm::nextMonth,
    )

    // Back closes an open (or opening) drawer before it can leave the app.
    val drawerOpen = drawerState.currentValue == DrawerValue.Open || drawerState.targetValue == DrawerValue.Open
    BackHandler(enabled = drawerOpen) { scope.launch { drawerState.close() } }

    if (showAbout) AboutDialog(onDismiss = { showAbout = false })
    if (confirmLogout) LogoutDialog(
        canSwitchAccount = canSwitchAccount,
        onLogout = {
            confirmLogout = false
            onLogout()
        },
        onDismiss = { confirmLogout = false },
    )

    // Close the drawer, then act: a screen opened from it finds the drawer closed on return.
    fun fromDrawer(action: () -> Unit) {
        scope.launch {
            drawerState.close()
            action()
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        drawerContent = {
            HomeDrawerContent(
                userName = userName,
                role = role,
                isSuperAdmin = isSuperAdmin,
                canMarksEntry = canMarksEntry,
                canResults = canResults,
                onDashboard = { scope.launch { drawerState.close() } },
                onTakeAttendance = { fromDrawer(onTakeAttendance) },
                onViewHistory = { fromDrawer(onViewHistory) },
                onViewStudents = { fromDrawer(onViewStudents) },
                onMarksEntry = { fromDrawer(onMarksEntry) },
                onResults = { fromDrawer(onResults) },
                onApprovals = { fromDrawer(onApprovals) },
                onNotices = { fromDrawer(onNotices) },
                onSettings = { fromDrawer(onSettings) },
                onAbout = { fromDrawer { showAbout = true } },
                canSwitchAccount = canSwitchAccount,
                onSwitchAccount = { fromDrawer(onSwitchAccount) },
                // Logout now forgets the account on this phone: ask first.
                onLogout = { fromDrawer { confirmLogout = true } },
            )
        },
    ) {
        Scaffold(
            topBar = {
                // Same colour as the top of the header gradient below, so the two read as one band.
                val brand = KISTheme.colors
                TopAppBar(
                    title = {
                        Text(
                            "Khalsa International",
                            fontFamily = PlayfairDisplay,
                            fontWeight = FontWeight.Bold,
                            maxLines = 1,
                            overflow = TextOverflow.Ellipsis,
                        )
                    },
                    navigationIcon = {
                        IconButton(onClick = { scope.launch { drawerState.open() } }) {
                            Icon(Icons.Default.Menu, contentDescription = "Open menu")
                        }
                    },
                    actions = {
                        // Spins while any card loads, and stays a button: a slow card never blocks a refresh.
                        val loading = cards.anyLoading
                        IconButton(
                            onClick = dashVm::refreshAll,
                            modifier = Modifier.semantics {
                                contentDescription = if (loading) "Refreshing the dashboard" else "Refresh the dashboard"
                            },
                        ) {
                            if (loading) {
                                CircularProgressIndicator(
                                    modifier = Modifier.size(22.dp),
                                    strokeWidth = 2.dp,
                                    color = brand.onTopBar,
                                )
                            } else {
                                Icon(Icons.Default.Refresh, contentDescription = null)
                            }
                        }
                    },
                    colors = TopAppBarDefaults.topAppBarColors(
                        containerColor = brand.loginGradientStart,
                        scrolledContainerColor = brand.loginGradientStart,
                        titleContentColor = brand.onTopBar,
                        navigationIconContentColor = brand.onTopBar,
                        actionIconContentColor = brand.onTopBar,
                    ),
                )
            }
        ) { padding: PaddingValues ->
            LazyColumn(
                Modifier
                    .fillMaxSize()
                    .padding(padding),
                contentPadding = PaddingValues(bottom = 24.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp),
            ) {
                item(key = "greeting") {
                    GreetingHeader(userName = userName, role = role)
                }
                if (cards.access.isAdmin) adminDashboard(cards, s, actions) else teacherDashboard(cards, s, actions)
            }
        }
    }
}

// ── Brand header ────────────────────────────────────────────────────────

private val HEADER_DATE: DateTimeFormatter = DateTimeFormatter.ofPattern("EEEE, d MMM yyyy", Locale.ENGLISH)

/** Lower-cased honorifics that stay with the name after them ("Mrs. Sharma", not "Mrs."). */
private val HONORIFICS = setOf("mr", "mrs", "ms", "miss", "dr", "prof", "sh", "smt", "s", "sardar")

/**
 * The name to greet: a teacher's first name ("Manjeet" for "Manjeet Kaur"), with a leading
 * honorific kept ("Mrs. Sharma"). Admin accounts are named after the account ("Super
 * Admin"), so theirs is used whole. Empty when there is no name.
 */
internal fun greetingName(name: String, role: String?): String {
    val words = name.trim().split(Regex("\\s+")).filter { it.isNotEmpty() }
    if (words.isEmpty()) return ""
    if (role == "admin" || role == "super_admin") return words.joinToString(" ")
    val first = words[0]
    return if (words.size > 1 && first.trimEnd('.').lowercase(Locale.ROOT) in HONORIFICS) "$first ${words[1]}" else first
}

/**
 * Full-width gradient band under the top bar: the crest, "Sat Sri Akal, {name}" in Playfair
 * Display, the role chip and today's date, closed by the royal-gold rule.
 */
@Composable
private fun GreetingHeader(userName: String, role: String?) {
    val onBrand = KISTheme.colors.onTopBar
    // Non-breaking spaces keep the name on one line: a greeting too long for the row wraps
    // after "Sat Sri Akal," rather than inside "Mrs. Sharma".
    val name = greetingName(userName, role).replace(' ', '\u00A0')
    Column(
        Modifier
            .fillMaxWidth()
            .background(brandGradient())
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(horizontal = 20.dp, vertical = 18.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            // The crest is 5:4, so only its height is fixed (CLAUDE.md Gotcha #11).
            Image(
                painter = painterResource(R.drawable.crest_mark),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.height(44.dp),
            )
            Spacer(Modifier.width(14.dp))
            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text(
                    if (name.isEmpty()) "Sat Sri Akal" else "Sat Sri Akal, $name",
                    fontFamily = PlayfairDisplay,
                    fontWeight = FontWeight.Bold,
                    style = MaterialTheme.typography.headlineSmall,
                    color = onBrand,
                )
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    roleLabel(role)?.let { RoleChip(it) }
                    Text(
                        HEADER_DATE.format(LocalDate.now()),
                        style = MaterialTheme.typography.bodySmall,
                        color = onBrand.copy(alpha = 0.85f),
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
        BrandRule()
    }
}

// ── Dialogs ─────────────────────────────────────────────────────────────

@Composable
private fun AboutDialog(onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        confirmButton = {
            TextButton(onClick = onDismiss) { Text("Close") }
        },
        title = { Text("KIS School Portal") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(Modifier.fillMaxWidth()) {
                    Text("Version", modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(BuildConfig.VERSION_NAME)
                }
                Row(Modifier.fillMaxWidth()) {
                    Text("Build", modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(BuildConfig.VERSION_CODE.toString())
                }
                Row(Modifier.fillMaxWidth()) {
                    Text("Package", modifier = Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(BuildConfig.APPLICATION_ID, style = MaterialTheme.typography.bodySmall)
                }
                HorizontalDivider(Modifier.padding(vertical = 4.dp))
                Text(
                    "Staff portal for KIS School. Built for the staff at kisschool.in.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    )
}

/**
 * Logout signs this phone out for good: the account leaves the phone's saved list and needs
 * its password next time. Switch account (when offered) keeps it saved instead.
 */
@Composable
private fun LogoutDialog(canSwitchAccount: Boolean, onLogout: () -> Unit, onDismiss: () -> Unit) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Log out?") },
        text = {
            Text(
                if (canSwitchAccount) {
                    "This account will be removed from this phone and you'll need your password to sign in again. " +
                        "To keep it saved, use Switch account instead."
                } else {
                    "You'll need your password to sign in again."
                }
            )
        },
        confirmButton = { TextButton(onClick = onLogout) { Text("Log out") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } },
    )
}
