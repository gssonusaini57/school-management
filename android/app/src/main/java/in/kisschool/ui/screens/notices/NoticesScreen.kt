package `in`.kisschool.ui.screens.notices

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.selection.SelectionContainer
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.SpanStyle
import androidx.compose.ui.text.buildAnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.text.withStyle
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.repo.Notice
import `in`.kisschool.data.repo.NoticePriority
import `in`.kisschool.ui.components.EmptyState
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import `in`.kisschool.ui.components.ModuleTopBarTitle
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisIcons
import `in`.kisschool.ui.theme.KisModule
import `in`.kisschool.ui.theme.SheetSystemBarsFollowAppTheme
import `in`.kisschool.ui.theme.kisTopAppBarColors
import `in`.kisschool.util.formatDateTime
import `in`.kisschool.util.relativeAge
import kotlinx.coroutines.delay
import java.time.Instant

/** The school's notices, newest first; tap one to read it in full. Read-only: posting is on the web. */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NoticesScreen(vm: NoticesViewModel, onBack: () -> Unit) {
    val s by vm.state.collectAsStateWithLifecycle()

    // "2 h ago" is measured against this, moved on each minute while the screen is open.
    var now by remember { mutableStateOf(Instant.now()) }
    LaunchedEffect(Unit) {
        while (true) {
            delay(60_000)
            now = Instant.now()
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { ModuleTopBarTitle("Notices", KisModule.Notices, KisIcons.Notices) },
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
            when {
                s.notices.isEmpty() && s.loading -> LoadingRow()
                s.notices.isEmpty() && s.error != null -> Column(
                    Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    ErrorBanner(s.error)
                    OutlinedButton(onClick = vm::load) { Text("Try again") }
                }
                s.notices.isEmpty() -> EmptyState("No notices yet.")
                else -> LazyColumn(
                    Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp),
                ) {
                    if (s.loading) {
                        item(key = "refreshing") { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                    }
                    s.error?.let { err -> item(key = "error") { ErrorBanner(err) } }
                    items(s.notices, key = { it.id }) { n ->
                        NoticeRow(n = n, now = now, onClick = { vm.open(n.id) })
                    }
                }
            }
        }
    }

    val open = s.notices.firstOrNull { it.id == s.openId }
    if (open != null) {
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(onDismissRequest = vm::close, sheetState = sheetState) {
            SheetSystemBarsFollowAppTheme()
            NoticeSheet(n = open)
        }
    }
}

/** High is the Approvals red, medium the Notices amber, normal the grey of "no status". */
@Composable
internal fun priorityColor(p: NoticePriority): Color = when (p) {
    NoticePriority.HIGH -> KISTheme.colors.module(KisModule.Approvals).fg
    NoticePriority.MEDIUM -> KISTheme.colors.module(KisModule.Notices).fg
    NoticePriority.NORMAL -> KISTheme.colors.noStatus
}

/** Spelled out for high and medium only: a normal notice needs no label. */
internal fun priorityLabel(p: NoticePriority): String? = when (p) {
    NoticePriority.HIGH -> "High priority"
    NoticePriority.MEDIUM -> "Medium priority"
    NoticePriority.NORMAL -> null
}

@Composable
internal fun PriorityDot(p: NoticePriority, modifier: Modifier = Modifier) {
    val color = priorityColor(p)
    val label = priorityLabel(p) ?: "Normal priority"
    Box(
        modifier
            .size(10.dp)
            .background(color, CircleShape)
            .semantics { contentDescription = label }
    )
}

private fun audienceText(audience: String): String? = when (val a = audience.trim().lowercase()) {
    "" -> null
    "all" -> "For everyone"
    else -> "For $a"
}

@Composable
private fun NoticeRow(n: Notice, now: Instant, onClick: () -> Unit) {
    val priority = priorityLabel(n.priority)
    val priorityTint = priorityColor(n.priority)
    val meta = buildAnnotatedString {
        if (priority != null) {
            withStyle(SpanStyle(color = priorityTint, fontWeight = FontWeight.SemiBold)) { append(priority) }
        }
        val rest = listOfNotNull(
            n.postedBy.ifBlank { null },
            n.createdAt?.let { relativeAge(it, now) },
        )
        if (rest.isNotEmpty()) {
            if (priority != null) append(" · ")
            append(rest.joinToString(" · "))
        }
    }
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth(),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .padding(16.dp),
            verticalAlignment = Alignment.Top,
        ) {
            PriorityDot(n.priority, Modifier.padding(top = 7.dp))
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(
                    n.title.ifBlank { "(No title)" },
                    style = MaterialTheme.typography.titleMedium,
                    maxLines = 2,
                    overflow = TextOverflow.Ellipsis,
                )
                if (n.content.isNotBlank()) {
                    Text(
                        n.content,
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 2,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
                if (meta.isNotEmpty()) {
                    Text(
                        meta,
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                }
            }
        }
    }
}

/** The whole notice: priority, title, who posted it and when, who it is for, then the full text. */
@Composable
private fun NoticeSheet(n: Notice) {
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
            .padding(bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        priorityLabel(n.priority)?.let { label ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                PriorityDot(n.priority)
                Spacer(Modifier.width(8.dp))
                Text(
                    label,
                    style = MaterialTheme.typography.labelLarge,
                    color = priorityColor(n.priority),
                )
            }
        }
        Text(n.title.ifBlank { "(No title)" }, style = MaterialTheme.typography.titleLarge)
        val meta = listOfNotNull(
            n.postedBy.ifBlank { null }?.let { "Posted by $it" },
            n.createdAt?.let { formatDateTime(it) },
            audienceText(n.audience),
        ).joinToString(" · ")
        if (meta.isNotEmpty()) {
            Text(
                meta,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        HorizontalDivider(Modifier.padding(vertical = 4.dp))
        SelectionContainer {
            Text(
                n.content.ifBlank { "No further details." },
                style = MaterialTheme.typography.bodyLarge,
            )
        }
    }
}
