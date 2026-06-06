package `in`.kisschool.ui.screens.approvals

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.horizontalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.DeletionRequestDto
import `in`.kisschool.data.api.dto.EditRequestDto
import `in`.kisschool.data.api.dto.MarksEditRequestDto
import `in`.kisschool.ui.components.EmptyState
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow

private enum class ApprovalTab { STUDENT, MARKS, DELETIONS }

private val OldRed = Color(0xFFB91C1C)
private val NewGreen = Color(0xFF15803D)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovalsScreen(vm: ApprovalsViewModel, onBack: () -> Unit) {
    val s by vm.state.collectAsStateWithLifecycle()
    var tab by remember { mutableStateOf(ApprovalTab.STUDENT) }
    var reviewing by remember { mutableStateOf<EditRequestDto?>(null) }
    var rejectAction by remember { mutableStateOf<((String?) -> Unit)?>(null) }
    var purgeTarget by remember { mutableStateOf<DeletionRequestDto?>(null) }

    rejectAction?.let { action ->
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { rejectAction = null },
            title = { Text("Reject request") },
            text = {
                OutlinedTextField(
                    value = reason,
                    onValueChange = { if (it.length <= 500) reason = it },
                    label = { Text("Reason (optional)") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth(),
                )
            },
            confirmButton = { TextButton(onClick = { action(reason.ifBlank { null }); rejectAction = null }) { Text("Reject") } },
            dismissButton = { TextButton(onClick = { rejectAction = null }) { Text("Cancel") } },
        )
    }

    purgeTarget?.let { t ->
        AlertDialog(
            onDismissRequest = { purgeTarget = null },
            title = { Text("Permanently delete?") },
            text = { Text("Purge \"${t.name}\" forever? This cannot be undone.") },
            confirmButton = {
                TextButton(onClick = { vm.purgeDeletion(t.kind, t.id); purgeTarget = null }) { Text("Purge") }
            },
            dismissButton = { TextButton(onClick = { purgeTarget = null }) { Text("Cancel") } },
        )
    }

    reviewing?.let { req ->
        EditReviewDialog(
            req = req,
            busy = s.busyId == "edit-${req.id}",
            onApprove = { vm.approveEdit(req.id); reviewing = null },
            onReject = { reviewing = null; rejectAction = { reason -> vm.rejectEdit(req.id, reason) } },
            onDismiss = { reviewing = null },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Approvals") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = vm::load) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        }
    ) { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                FilterChip(selected = tab == ApprovalTab.STUDENT, onClick = { tab = ApprovalTab.STUDENT },
                    label = { Text("Student edits (${s.edits.size})") })
                FilterChip(selected = tab == ApprovalTab.MARKS, onClick = { tab = ApprovalTab.MARKS },
                    label = { Text("Marks edits (${s.marks.size})") })
                FilterChip(selected = tab == ApprovalTab.DELETIONS, onClick = { tab = ApprovalTab.DELETIONS },
                    label = { Text("Deletions (${s.deletions.size})") })
            }

            ErrorBanner(s.actionError)
            ErrorBanner(s.error)

            if (s.loading) {
                LoadingRow()
            } else when (tab) {
                ApprovalTab.STUDENT ->
                    if (s.edits.isEmpty()) EmptyState("No pending student edits.")
                    else LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(s.edits, key = { it.id }) { req -> EditCard(req, onReview = { reviewing = req }) }
                    }
                ApprovalTab.MARKS ->
                    if (s.marks.isEmpty()) EmptyState("No pending marks edits.")
                    else LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(s.marks, key = { it.id }) { req ->
                            MarksCard(
                                req = req,
                                busy = s.busyId == "marks-${req.id}",
                                onApprove = { vm.approveMarks(req.id) },
                                onReject = { rejectAction = { reason -> vm.rejectMarks(req.id, reason) } },
                            )
                        }
                    }
                ApprovalTab.DELETIONS ->
                    if (s.deletions.isEmpty()) EmptyState("No deletion requests.")
                    else LazyColumn(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        items(s.deletions, key = { "${it.kind}-${it.id}" }) { req ->
                            DeletionCard(
                                req = req,
                                busy = s.busyId == "del-${req.kind}-${req.id}",
                                onApprove = { vm.approveDeletion(req.kind, req.id) },
                                onRestore = { vm.restoreDeletion(req.kind, req.id) },
                                onPurge = { purgeTarget = req },
                            )
                        }
                    }
            }
        }
    }
}

@Composable
private fun EditCard(req: EditRequestDto, onReview: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(req.studentName, style = MaterialTheme.typography.titleMedium)
            Text(
                buildString {
                    req.className?.let { append(it).append(" · ") }
                    append("${req.changes.size} field(s)")
                },
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Text(
                "by ${req.requestedBy ?: "—"}${req.requestedByRole?.let { " ($it)" } ?: ""}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
                Button(onClick = onReview) { Text("Review") }
            }
        }
    }
}

@Composable
private fun EditReviewDialog(
    req: EditRequestDto,
    busy: Boolean,
    onApprove: () -> Unit,
    onReject: () -> Unit,
    onDismiss: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(req.studentName) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                req.className?.let {
                    Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                HorizontalDivider()
                req.changes.forEach { (key, pair) ->
                    Column(Modifier.fillMaxWidth()) {
                        Text(fieldLabel(key), style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.Medium)
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Text(
                                diffValue(pair.old),
                                style = MaterialTheme.typography.bodySmall,
                                color = OldRed,
                                textDecoration = TextDecoration.LineThrough,
                                modifier = Modifier.weight(1f),
                            )
                            Text("→", modifier = Modifier.padding(horizontal = 6.dp))
                            Text(
                                diffValue(pair.new),
                                style = MaterialTheme.typography.bodySmall,
                                color = NewGreen,
                                fontWeight = FontWeight.Medium,
                                modifier = Modifier.weight(1f),
                            )
                        }
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onApprove, enabled = !busy) { Text(if (busy) "…" else "Approve") }
        },
        dismissButton = {
            TextButton(onClick = onReject, enabled = !busy) { Text("Reject") }
        },
    )
}

@Composable
private fun MarksCard(req: MarksEditRequestDto, busy: Boolean, onApprove: () -> Unit, onReject: () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("${req.className} · ${req.subject}", style = MaterialTheme.typography.titleMedium)
            Text(
                "${req.examType} · ${req.session} · ${req.studentCount} students",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            req.reason?.takeIf { it.isNotBlank() }?.let {
                Text("Reason: $it", style = MaterialTheme.typography.bodySmall)
            }
            Text(
                "by ${req.requestedBy ?: "—"}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End)) {
                OutlinedButton(onClick = onReject, enabled = !busy) { Text("Reject") }
                Button(onClick = onApprove, enabled = !busy) {
                    if (busy) CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.padding(2.dp))
                    else Text("Approve")
                }
            }
        }
    }
}

@Composable
private fun DeletionCard(
    req: DeletionRequestDto,
    busy: Boolean,
    onApprove: () -> Unit,
    onRestore: () -> Unit,
    onPurge: () -> Unit,
) {
    val pending = req.status == "pending_delete"
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text("${req.name}  ·  ${req.kind}", style = MaterialTheme.typography.titleMedium)
            (req.className ?: req.designation)?.let {
                Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(
                if (pending) "Pending deletion" else "Archived (deleted)",
                style = MaterialTheme.typography.labelSmall,
                color = if (pending) Color(0xFFD97706) else MaterialTheme.colorScheme.error,
            )
            req.deleteReason?.takeIf { it.isNotBlank() }?.let {
                Text("Reason: $it", style = MaterialTheme.typography.bodySmall)
            }
            req.deleteRequestedBy?.let {
                Text("by $it", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp, Alignment.End)) {
                OutlinedButton(onClick = onRestore, enabled = !busy) { Text("Restore") }
                if (pending) {
                    Button(onClick = onApprove, enabled = !busy) { Text("Approve delete") }
                } else {
                    Button(onClick = onPurge, enabled = !busy) { Text("Purge") }
                }
            }
        }
    }
}

private fun fieldLabel(key: String): String =
    key.split("_").joinToString(" ") { part -> part.replaceFirstChar { it.uppercase() } }

private fun diffValue(v: Any?): String = when (v) {
    null -> "—"
    is Double -> if (v % 1.0 == 0.0) v.toLong().toString() else v.toString()
    is String -> v.ifBlank { "—" }
    else -> v.toString()
}
