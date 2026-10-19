package `in`.kisschool.ui.screens.classestoday

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.outlined.BeachAccess
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.ClassAttendanceRowDto
import `in`.kisschool.ui.components.AccentStripWidth
import `in`.kisschool.ui.components.EmptyState
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import `in`.kisschool.ui.components.ModuleIconCircle
import `in`.kisschool.ui.components.ModuleTopBarTitle
import `in`.kisschool.ui.components.accentStrip
import `in`.kisschool.ui.screens.dashboard.ClassDayKind
import `in`.kisschool.ui.screens.dashboard.PercentBar
import `in`.kisschool.ui.screens.dashboard.dayKind
import `in`.kisschool.ui.screens.dashboard.formatPercent
import `in`.kisschool.ui.screens.dashboard.plural
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisIcons
import `in`.kisschool.ui.theme.KisModule
import `in`.kisschool.ui.theme.kisTopAppBarColors
import java.time.format.DateTimeFormatter
import java.util.Locale

private val DAY_MONTH: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM", Locale.ENGLISH)

private fun ClassDayKind.icon(): ImageVector = when (this) {
    ClassDayKind.MARKED -> KisIcons.ClassesMarked
    ClassDayKind.PENDING -> KisIcons.NotMarked
    ClassDayKind.HOLIDAY -> Icons.Outlined.BeachAccess
}

private fun ClassDayKind.title(date: String): String = when (this) {
    ClassDayKind.MARKED -> "Marked classes · $date"
    ClassDayKind.PENDING -> "Pending classes · $date"
    ClassDayKind.HOLIDAY -> "Classes on holiday · $date"
}

private fun summaryText(kind: ClassDayKind, n: Int, total: Int): String {
    val verb = if (n == 1) "is" else "are"
    return when (kind) {
        ClassDayKind.MARKED -> "$n of ${plural(total, "class")} ${if (n == 1) "has" else "have"} marked attendance."
        ClassDayKind.PENDING -> "$n of ${plural(total, "class")} $verb still to be marked."
        ClassDayKind.HOLIDAY -> "$n of ${plural(total, "class")} $verb on holiday."
    }
}

private fun emptyText(kind: ClassDayKind, date: String): String = when (kind) {
    ClassDayKind.MARKED -> "No class has marked attendance for $date yet."
    ClassDayKind.PENDING -> "Every class has attendance or a holiday for $date."
    ClassDayKind.HOLIDAY -> "No class is on holiday on $date."
}

/**
 * One day's marked, pending or holiday classes in school order, opened from the dashboard's
 * classes ring. Pending classes each have Take attendance; a marked or holiday class opens
 * that day's register. Back returns to the dashboard.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ClassesTodayScreen(
    vm: ClassesTodayViewModel,
    onBack: () -> Unit,
    onOpenAttendance: (className: String, iso: String) -> Unit,
) {
    val s by vm.state.collectAsStateWithLifecycle()
    val kind = vm.kind
    val iso = vm.date.toString()
    val dateLabel = DAY_MONTH.format(vm.date)

    Scaffold(
        topBar = {
            TopAppBar(
                title = { ModuleTopBarTitle(kind.title(dateLabel), KisModule.Attendance, kind.icon()) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = vm::load, enabled = !s.loading) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                },
                colors = kisTopAppBarColors(),
            )
        }
    ) { padding ->
        Box(
            Modifier
                .fillMaxSize()
                .padding(padding)
        ) {
            val all = s.classes
            val unavailable = s.unavailable
            when {
                unavailable != null -> EmptyState(unavailable)
                all == null && s.error != null -> Column(
                    Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    ErrorBanner(s.error)
                    OutlinedButton(onClick = vm::load) { Text("Try again") }
                }
                all == null -> LoadingRow()
                else -> {
                    val rows = all.filter { it.dayKind() == kind }
                    LazyColumn(
                        Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp),
                    ) {
                        if (s.loading) item(key = "refreshing") { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                        s.error?.let { err -> item(key = "error") { ErrorBanner(err) } }
                        item(key = "summary") {
                            Text(
                                summaryText(kind, rows.size, all.size),
                                style = MaterialTheme.typography.bodyMedium,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                            )
                        }
                        if (rows.isEmpty()) item(key = "empty") { EmptyState(emptyText(kind, dateLabel)) }
                        items(rows, key = { it.className }) { row ->
                            val open = { onOpenAttendance(row.className, iso) }
                            when (kind) {
                                ClassDayKind.PENDING -> PendingClassRow(row, open)
                                ClassDayKind.MARKED -> MarkedClassRow(row, open)
                                ClassDayKind.HOLIDAY -> HolidayClassRow(row, open)
                            }
                        }
                    }
                }
            }
        }
    }
}

/** A list card in the Attendance accent: the 4.dp strip down its start edge. */
@Composable
private fun ClassCard(onClick: (() -> Unit)?, content: @Composable ColumnScope.() -> Unit) {
    val accent = KISTheme.colors.module(KisModule.Attendance)
    val elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    val body: @Composable ColumnScope.() -> Unit = {
        Column(
            Modifier
                .fillMaxWidth()
                .accentStrip(accent.strip)
                .padding(start = AccentStripWidth + 16.dp, end = 16.dp, top = 14.dp, bottom = 14.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
            content = content,
        )
    }
    if (onClick != null) {
        Card(onClick = onClick, modifier = Modifier.fillMaxWidth(), elevation = elevation, content = body)
    } else {
        Card(modifier = Modifier.fillMaxWidth(), elevation = elevation, content = body)
    }
}

@Composable
private fun ClassHeading(row: ClassAttendanceRowDto, icon: ImageVector, detail: String, trailing: @Composable () -> Unit) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        ModuleIconCircle(module = KisModule.Attendance, icon = icon)
        Column(
            Modifier
                .weight(1f)
                .padding(start = 12.dp, end = 8.dp)
        ) {
            Text(
                row.className,
                style = MaterialTheme.typography.titleMedium,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        trailing()
    }
}

@Composable
private fun PendingClassRow(row: ClassAttendanceRowDto, onTakeAttendance: () -> Unit) {
    ClassCard(onClick = null) {
        ClassHeading(row, KisIcons.NotMarked, plural(row.classSize, "student")) {
            FilledTonalButton(
                onClick = onTakeAttendance,
                modifier = Modifier.semantics { contentDescription = "Take attendance for ${row.className}" },
            ) { Text("Take attendance") }
        }
    }
}

@Composable
private fun MarkedClassRow(row: ClassAttendanceRowDto, onOpen: () -> Unit) {
    val pct = row.percent
    ClassCard(onClick = onOpen) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                row.className,
                style = MaterialTheme.typography.titleMedium,
                modifier = Modifier.weight(1f),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            Text(
                pct?.let { "${formatPercent(it)} present" } ?: "—",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
            )
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier
                    .padding(start = 4.dp)
                    .size(20.dp),
            )
        }
        PercentBar(pct, KISTheme.colors.attendanceBand(pct))
        if (row.records == 0) {
            Text("Saved with no students", style = MaterialTheme.typography.bodyMedium)
        } else {
            val ofClass = if (row.records < row.classSize) " · class of ${row.classSize}" else ""
            Text("${row.present} / ${row.records} present$ofClass", style = MaterialTheme.typography.bodyMedium)
            Text(
                "Present ${row.present} · Absent ${row.absent} · Leave ${row.leave} · Half day ${row.halfDay}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun HolidayClassRow(row: ClassAttendanceRowDto, onOpen: () -> Unit) {
    ClassCard(onClick = onOpen) {
        ClassHeading(row, Icons.Outlined.BeachAccess, "Holiday · ${plural(row.classSize, "student")}") {
            Spacer(Modifier.width(4.dp))
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.size(20.dp),
            )
        }
    }
}
