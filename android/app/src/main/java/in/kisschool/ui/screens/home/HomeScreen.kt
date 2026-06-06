package `in`.kisschool.ui.screens.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.automirrored.filled.FactCheck
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.EditNote
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.People
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import `in`.kisschool.BuildConfig
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.screens.dashboard.DashboardViewModel
import `in`.kisschool.ui.screens.dashboard.MonthCalendar
import java.time.LocalDate
import java.time.YearMonth

private val MarkedGreen = Color(0xFF16A34A)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(
    userName: String,
    dashVm: DashboardViewModel,
    onOpenAttendanceFor: (className: String, iso: String) -> Unit,
    onTakeAttendance: () -> Unit,
    onViewHistory: () -> Unit,
    onViewStudents: () -> Unit,
    onMarksEntry: () -> Unit,
    onLogout: () -> Unit,
    isSuperAdmin: Boolean = false,
    onApprovals: () -> Unit = {},
) {
    var menuOpen by remember { mutableStateOf(false) }
    var showAbout by remember { mutableStateOf(false) }
    val s by dashVm.state.collectAsStateWithLifecycle()

    if (showAbout) AboutDialog(onDismiss = { showAbout = false })

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("KIS School Portal") },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                ),
                actions = {
                    IconButton(onClick = { menuOpen = true }) {
                        Icon(Icons.Default.MoreVert, contentDescription = "Menu")
                    }
                    DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                        DropdownMenuItem(
                            text = { Text("About") },
                            leadingIcon = { Icon(Icons.Default.Info, contentDescription = null) },
                            onClick = {
                                menuOpen = false
                                showAbout = true
                            }
                        )
                        DropdownMenuItem(
                            text = { Text("Logout") },
                            leadingIcon = { Icon(Icons.AutoMirrored.Filled.Logout, contentDescription = null) },
                            onClick = {
                                menuOpen = false
                                onLogout()
                            }
                        )
                    }
                }
            )
        }
    ) { padding: PaddingValues ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            Text(
                "Hello, $userName",
                style = MaterialTheme.typography.headlineSmall
            )

            // ── Attendance coverage dashboard ───────────────────────────────
            Card(
                modifier = Modifier.fillMaxWidth(),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column(
                    Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp)
                ) {
                    Text("Attendance coverage", style = MaterialTheme.typography.titleMedium)

                    ClassDropdown(
                        classes = s.allowedClasses,
                        selected = s.selectedClass,
                        onSelect = dashVm::selectClass,
                        modifier = Modifier.fillMaxWidth()
                    )

                    val cls = s.selectedClass
                    if (cls == null) {
                        Text(
                            "No classes assigned yet.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    } else {
                        val todayIsoStr = LocalDate.now().toString()
                        val todayMarked = s.month == YearMonth.now() && todayIsoStr in s.markedDates
                        TodayStatusChip(
                            marked = todayMarked,
                            onClick = { onOpenAttendanceFor(cls, todayIsoStr) }
                        )

                        MonthCalendar(
                            month = s.month,
                            markedDates = s.markedDates,
                            holidays = s.holidays,
                            today = LocalDate.now(),
                            onPrevMonth = dashVm::prevMonth,
                            onNextMonth = dashVm::nextMonth,
                            onDayClick = { iso -> onOpenAttendanceFor(cls, iso) },
                        )
                    }

                    ErrorBanner(s.error)
                }
            }

            // ── Quick actions ──────────────────────────────────────────────
            if (isSuperAdmin) {
                ActionTile(
                    title = "Approvals",
                    subtitle = "Review student & marks edits, deletions",
                    icon = Icons.AutoMirrored.Filled.FactCheck,
                    onClick = onApprovals
                )
            }
            ActionTile(
                title = "Take attendance",
                subtitle = "Mark today's class attendance",
                icon = Icons.Default.CalendarMonth,
                onClick = onTakeAttendance
            )
            ActionTile(
                title = "Past attendance",
                subtitle = "View previously saved records",
                icon = Icons.Default.History,
                onClick = onViewHistory
            )
            ActionTile(
                title = "Students",
                subtitle = "Browse class rosters",
                icon = Icons.Default.People,
                onClick = onViewStudents
            )
            ActionTile(
                title = "Marks entry",
                subtitle = "Enter marks · save draft · submit for lock",
                icon = Icons.Default.EditNote,
                onClick = onMarksEntry
            )
        }
    }
}

@Composable
private fun TodayStatusChip(marked: Boolean, onClick: () -> Unit) {
    val bg = if (marked) MarkedGreen.copy(alpha = 0.14f) else MaterialTheme.colorScheme.secondaryContainer
    val fg = if (marked) MarkedGreen else MaterialTheme.colorScheme.onSecondaryContainer
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .background(bg)
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        if (marked) {
            Icon(Icons.Default.CheckCircle, contentDescription = null, tint = fg)
            Text(
                "Today's attendance is marked",
                color = fg,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(start = 8.dp)
            )
        } else {
            Icon(Icons.Default.CalendarMonth, contentDescription = null, tint = fg)
            Text(
                "Mark today's attendance →",
                color = fg,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(start = 8.dp)
            )
        }
    }
}

@Composable
private fun ActionTile(
    title: String,
    subtitle: String,
    icon: ImageVector,
    onClick: () -> Unit
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .height(96.dp),
        onClick = onClick,
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Row(
            Modifier
                .fillMaxSize()
                .padding(16.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.height(36.dp)
            )
            Column(Modifier.padding(start = 16.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium)
                Text(
                    subtitle,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

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
