package `in`.kisschool.ui.screens.marks

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
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
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.ErrorBanner

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MarksEntryScreen(vm: MarksEntryViewModel, onBack: () -> Unit) {
    val s by vm.state.collectAsStateWithLifecycle()
    var showSubmit by remember { mutableStateOf(false) }
    var showRequest by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Marks entry") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        LazyColumn(
            Modifier.fillMaxSize().padding(padding).padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item { Box(Modifier.height(4.dp)) }

            // ── Selection controls ──────────────────────────────────────────
            item {
                ClassDropdown(
                    classes = s.classOptions,
                    selected = s.cls,
                    onSelect = vm::setClass,
                    label = "Class",
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                ClassDropdown(
                    classes = s.subjects.map { it.subjectName },
                    selected = s.subject?.subjectName,
                    onSelect = { name -> s.subjects.firstOrNull { it.subjectName == name }?.let(vm::setSubject) },
                    label = "Subject",
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                val labels = s.components.map { "${it.componentName} — max ${it.maxMarks}" }
                val selectedLabel = s.component?.let { "${it.componentName} — max ${it.maxMarks}" }
                ClassDropdown(
                    classes = labels,
                    selected = selectedLabel,
                    onSelect = { label ->
                        s.components.firstOrNull { "${it.componentName} — max ${it.maxMarks}" == label }
                            ?.let(vm::setComponent)
                    },
                    label = "Test / component",
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                OutlinedTextField(
                    value = s.session,
                    onValueChange = vm::setSession,
                    label = { Text("Session") },
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )
            }

            // ── Status + banners ────────────────────────────────────────────
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val statusLabel = when {
                        s.batch == null -> "New"
                        s.batch?.status == "draft" -> "Draft"
                        else -> "Submitted (locked)"
                    }
                    AssistChip(onClick = {}, label = { Text(statusLabel) })
                    if (s.component != null) {
                        Text(
                            "  Max marks: ${s.maxMarks}",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    if (s.loadingBatch || s.loadingRoster) {
                        CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.height(18.dp).padding(start = 8.dp))
                    }
                }
            }
            if (s.pending) item { Banner("An edit request is pending super-admin review. The batch unlocks once approved.", warn = true) }
            if (!s.pending && s.locked) item { Banner("This batch is submitted and locked. Use \"Request edit\" to ask a super-admin to unlock it.", warn = true) }
            s.batch?.lastRejection?.let { rej ->
                if (!s.pending) item { Banner("Previous edit request rejected: $rej", warn = false) }
            }

            // ── Roster ──────────────────────────────────────────────────────
            if (s.ready && s.students.isNotEmpty()) {
                item { HorizontalDivider() }
                items(s.students, key = { it.id }) { stu ->
                    MarkRow(
                        student = stu,
                        value = s.marks[stu.id] ?: "",
                        maxMarks = s.maxMarks,
                        enabled = s.editable && !s.busy,
                        onChange = { vm.setMark(stu.id, it) }
                    )
                }
            } else if (s.ready) {
                item { Text("No students in this class.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
            } else {
                item { Text("Pick class, subject, test and session to load the roster.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
            }

            // ── Messages + actions ──────────────────────────────────────────
            if (s.overMaxCount > 0) item {
                Text(
                    "Fix ${s.overMaxCount} mark(s) above ${s.maxMarks} before saving.",
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodySmall
                )
            }
            item { ErrorBanner(s.error) }
            s.message?.let { msg -> item { Banner(msg, warn = true, success = true) } }

            if (s.ready) item {
                Row(Modifier.fillMaxWidth().padding(vertical = 6.dp), horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    if (s.editable) {
                        OutlinedButton(onClick = vm::saveDraft, enabled = s.canSave, modifier = Modifier.weight(1f)) {
                            Text("Save draft")
                        }
                        Button(onClick = { showSubmit = true }, enabled = s.canSave, modifier = Modifier.weight(1f)) {
                            Text("Submit final")
                        }
                    } else if (s.pending) {
                        Button(onClick = {}, enabled = false, modifier = Modifier.fillMaxWidth()) {
                            Text("Edit request pending…")
                        }
                    } else {
                        Button(onClick = { showRequest = true }, enabled = !s.busy, modifier = Modifier.fillMaxWidth()) {
                            Text("Request edit")
                        }
                    }
                }
            }
            item { Box(Modifier.height(16.dp)) }
        }
    }

    if (showSubmit) {
        AlertDialog(
            onDismissRequest = { showSubmit = false },
            title = { Text("Submit final marks?") },
            text = { Text("After submitting, the batch is locked. To change it later you'll have to request a super-admin's approval.") },
            confirmButton = {
                TextButton(onClick = { showSubmit = false; vm.submit() }) { Text("Submit") }
            },
            dismissButton = { TextButton(onClick = { showSubmit = false }) { Text("Cancel") } }
        )
    }

    if (showRequest) {
        var reason by remember { mutableStateOf("") }
        AlertDialog(
            onDismissRequest = { showRequest = false },
            title = { Text("Request permission to edit") },
            text = {
                Column {
                    Text("This batch is locked. Tell the super-admin why you need to edit — they'll approve or reject it.")
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { if (it.length <= 2000) reason = it },
                        label = { Text("Reason") },
                        minLines = 3,
                        modifier = Modifier.fillMaxWidth().padding(top = 8.dp)
                    )
                    Text("${reason.trim().length}/2000", style = MaterialTheme.typography.labelSmall)
                }
            },
            confirmButton = {
                TextButton(
                    onClick = { showRequest = false; vm.requestEdit(reason.trim()) },
                    enabled = reason.trim().isNotEmpty()
                ) { Text("Send request") }
            },
            dismissButton = { TextButton(onClick = { showRequest = false }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun MarkRow(
    student: StudentDto,
    value: String,
    maxMarks: Int,
    enabled: Boolean,
    onChange: (String) -> Unit,
) {
    val invalid = value.isNotBlank() && (value.toIntOrNull() ?: 0) > maxMarks
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Text(
            student.rollNo?.ifBlank { "—" } ?: "—",
            modifier = Modifier.width(34.dp),
            textAlign = TextAlign.End,
            fontFamily = FontFamily.Monospace,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Column(Modifier.weight(1f).padding(horizontal = 10.dp)) {
            Text(student.name, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
            if (!student.father.isNullOrBlank()) {
                Text(
                    "S/o ${student.father}",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1, overflow = TextOverflow.Ellipsis
                )
            }
        }
        OutlinedTextField(
            value = value,
            onValueChange = onChange,
            singleLine = true,
            isError = invalid,
            enabled = enabled,
            placeholder = { Text("—") },
            keyboardOptions = KeyboardOptions(keyboardType = androidx.compose.ui.text.input.KeyboardType.Number),
            modifier = Modifier.width(96.dp)
        )
    }
}

@Composable
private fun Banner(text: String, warn: Boolean, success: Boolean = false) {
    val bg = when {
        success -> MaterialTheme.colorScheme.secondaryContainer
        warn -> MaterialTheme.colorScheme.tertiaryContainer
        else -> MaterialTheme.colorScheme.errorContainer
    }
    val fg = when {
        success -> MaterialTheme.colorScheme.onSecondaryContainer
        warn -> MaterialTheme.colorScheme.onTertiaryContainer
        else -> MaterialTheme.colorScheme.onErrorContainer
    }
    Box(Modifier.fillMaxWidth().background(bg, RoundedCornerShape(8.dp)).padding(12.dp)) {
        Text(text, color = fg, style = MaterialTheme.typography.bodySmall)
    }
}
