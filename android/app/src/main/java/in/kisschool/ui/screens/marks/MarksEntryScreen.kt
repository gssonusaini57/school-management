package `in`.kisschool.ui.screens.marks

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.filled.ArrowDropDown
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.AssistChip
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.ExamComponentDto
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.ErrorBanner

/** Dropdown label for a test; graded tests (max 0) say so instead of "max 0". */
private fun componentLabel(c: ExamComponentDto): String =
    if (c.maxMarks == 0) "${c.componentName} — grade" else "${c.componentName} — max ${c.maxMarks}"

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MarksEntryScreen(vm: MarksEntryViewModel, onBack: () -> Unit) {
    val s by vm.state.collectAsStateWithLifecycle()
    var showSubmit by remember { mutableStateOf(false) }
    var showRequest by remember { mutableStateOf(false) }
    /** A selection change (or leaving) waiting for the teacher to agree to lose the typed marks. */
    var discardThen by remember { mutableStateOf<(() -> Unit)?>(null) }

    /** Run [action] now, or once the teacher confirms, when it would lose typed marks. */
    fun unlessDirty(action: () -> Unit) {
        if (s.dirty) discardThen = action else action()
    }

    BackHandler(enabled = s.dirty) { discardThen = onBack }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Marks entry") },
                navigationIcon = {
                    IconButton(onClick = { unlessDirty(onBack) }) {
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
                    onSelect = { c -> unlessDirty { vm.setClass(c) } },
                    label = "Class",
                    enabled = !s.busy,
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                ClassDropdown(
                    classes = s.subjects.map { it.subjectName },
                    selected = s.subject?.subjectName,
                    onSelect = { name ->
                        s.subjects.firstOrNull { it.subjectName == name }?.let { sub -> unlessDirty { vm.setSubject(sub) } }
                    },
                    label = "Subject",
                    enabled = !s.busy,
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                ClassDropdown(
                    classes = s.components.map(::componentLabel),
                    selected = s.component?.let(::componentLabel),
                    onSelect = { label ->
                        s.components.firstOrNull { componentLabel(it) == label }?.let { c -> unlessDirty { vm.setComponent(c) } }
                    },
                    label = "Test / component",
                    enabled = !s.busy,
                    modifier = Modifier.fillMaxWidth()
                )
            }
            item {
                if (s.sessionOptions.isNotEmpty()) {
                    // The server's sessions: a pick reloads the marks for that year.
                    ClassDropdown(
                        classes = s.sessionOptions,
                        selected = s.session,
                        onSelect = { v -> if (v != s.session) unlessDirty { vm.pickSession(v) } },
                        label = "Session",
                        enabled = !s.busy,
                        modifier = Modifier.fillMaxWidth()
                    )
                } else {
                    // Offline or an older server: type it (e.g. 2026-27).
                    OutlinedTextField(
                        value = s.session,
                        onValueChange = { v -> if (v != s.session) unlessDirty { vm.setSession(v) } },
                        label = { Text("Session") },
                        singleLine = true,
                        enabled = !s.busy,
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            }

            // ── Status + banners ────────────────────────────────────────────
            item {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    val statusLabel = when {
                        s.ready && !s.marksLoaded -> if (s.loadingBatch) "Loading…" else "Not loaded"
                        s.batch == null -> "New"
                        s.batch?.status == "draft" -> "Draft"
                        s.isSuperAdmin -> "Submitted"
                        else -> "Submitted (locked)"
                    }
                    AssistChip(onClick = {}, label = { Text(statusLabel) })
                    if (s.component != null) {
                        Text(
                            if (s.isGraded) "  Letter grade" else "  Max marks: ${s.maxMarks}",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    if (s.loadingBatch || s.loadingRoster) {
                        CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.height(18.dp).padding(start = 8.dp))
                    }
                }
            }
            if (s.pending) item {
                Banner(
                    if (s.isSuperAdmin) "A teacher's edit request for these marks is waiting. Approve or reject it in Approvals before changing them here."
                    else "An edit request is pending super-admin review. The batch unlocks once approved.",
                    warn = true
                )
            }
            if (!s.pending && s.lockedForMe) item { Banner("This batch is submitted and locked. Use \"Request edit\" to ask a super-admin to unlock it.", warn = true) }
            if (!s.pending && s.locked && s.isSuperAdmin) item {
                Banner("These marks are submitted. As super-admin you can change them directly; they stay submitted.", warn = true)
            }
            s.batch?.lastRejection?.let { rej ->
                if (!s.pending) item { Banner("Previous edit request rejected: $rej", warn = false) }
            }

            // ── Roster ──────────────────────────────────────────────────────
            if (s.ready && !s.marksLoaded && !s.loadingBatch) {
                // A save from an empty roster would delete the marks already saved, so the
                // rows wait until this selection's marks have loaded.
                item {
                    Text(
                        if (s.batchLoadFailed) "The saved marks couldn't be loaded. Retry below before entering marks."
                        else "Load the saved marks for this session before entering marks.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            } else if (s.ready && s.students.isNotEmpty()) {
                item { HorizontalDivider() }
                items(s.students, key = { it.id }) { stu ->
                    if (s.isGraded) {
                        GradeRow(
                            student = stu,
                            letter = s.marks[stu.id].orEmpty(),
                            letters = s.gradeLetters,
                            enabled = s.canEdit,
                            onPick = { vm.setGrade(stu.id, it) }
                        )
                    } else {
                        MarkRow(
                            student = stu,
                            value = s.marks[stu.id] ?: "",
                            maxMarks = s.maxMarks,
                            enabled = s.canEdit,
                            onChange = { vm.setMark(stu.id, it) }
                        )
                    }
                }
            } else if (s.ready) {
                item { Text("No students in this class.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
            } else if (s.classOptions.isEmpty()) {
                item { Text("No classes assigned yet.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
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
                    when {
                        // This selection's saved marks aren't on screen yet (loading, failed, or a
                        // retyped session): load them first. Nothing can be saved before that.
                        !s.marksLoaded -> {
                            OutlinedButton(
                                onClick = vm::loadBatch,
                                enabled = !s.loadingBatch && !s.busy,
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Text(
                                    when {
                                        s.loadingBatch -> "Loading marks…"
                                        s.batchLoadFailed -> "Retry loading marks"
                                        else -> "Load marks"
                                    }
                                )
                            }
                        }
                        // Super-admin on a submitted batch: save in place, no submit, never "Request edit".
                        s.locked && s.isSuperAdmin -> {
                            Button(onClick = vm::saveDraft, enabled = s.canSave, modifier = Modifier.fillMaxWidth()) {
                                Text("Save changes")
                            }
                        }
                        s.editable -> {
                            OutlinedButton(onClick = vm::saveDraft, enabled = s.canSave, modifier = Modifier.weight(1f)) {
                                Text("Save draft")
                            }
                            Button(onClick = { showSubmit = true }, enabled = s.canSubmit, modifier = Modifier.weight(1f)) {
                                Text("Submit final")
                            }
                        }
                        s.pending -> {
                            Button(onClick = {}, enabled = false, modifier = Modifier.fillMaxWidth()) {
                                Text("Edit request pending…")
                            }
                        }
                        else -> {
                            Button(onClick = { showRequest = true }, enabled = !s.busy, modifier = Modifier.fillMaxWidth()) {
                                Text("Request edit")
                            }
                        }
                    }
                }
            }
            item { Box(Modifier.height(16.dp)) }
        }
    }

    discardThen?.let { then ->
        AlertDialog(
            onDismissRequest = { discardThen = null },
            title = { Text("Discard unsaved marks?") },
            text = { Text("The marks typed here aren't saved yet. Save them first to keep them.") },
            confirmButton = { TextButton(onClick = { discardThen = null; then() }) { Text("Discard") } },
            dismissButton = { TextButton(onClick = { discardThen = null }) { Text("Keep editing") } }
        )
    }

    if (showSubmit) {
        AlertDialog(
            onDismissRequest = { showSubmit = false },
            title = { Text("Submit final marks?") },
            text = {
                Text(
                    if (s.isSuperAdmin) "After submitting, the batch is locked for teachers. You can still change it as super-admin."
                    else "After submitting, the batch is locked. To change it later you'll have to request a super-admin's approval."
                )
            },
            confirmButton = {
                TextButton(onClick = { showSubmit = false; vm.submit() }) { Text("Submit") }
            },
            dismissButton = { TextButton(onClick = { showSubmit = false }) { Text("Cancel") } }
        )
    }

    if (showRequest && !s.isSuperAdmin) {
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
private fun StudentLabel(student: StudentDto, modifier: Modifier) {
    Column(modifier.padding(horizontal = 10.dp)) {
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
}

@Composable
private fun RollText(student: StudentDto) {
    Text(
        student.rollNo?.ifBlank { "—" } ?: "—",
        modifier = Modifier.width(34.dp),
        textAlign = TextAlign.End,
        fontFamily = FontFamily.Monospace,
        color = MaterialTheme.colorScheme.onSurfaceVariant
    )
}

@Composable
private fun MarkRow(
    student: StudentDto,
    value: String,
    maxMarks: Int,
    enabled: Boolean,
    onChange: (String) -> Unit,
) {
    val invalid = value.isNotBlank() && (value.toIntOrNull() ?: Int.MAX_VALUE) > maxMarks
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        RollText(student)
        StudentLabel(student, Modifier.weight(1f))
        OutlinedTextField(
            value = value,
            onValueChange = onChange,
            singleLine = true,
            isError = invalid,
            enabled = enabled,
            placeholder = { Text("—") },
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            modifier = Modifier.width(96.dp)
        )
    }
}

/** A graded exam: pick a letter (or "—" to clear) instead of typing marks. */
@Composable
private fun GradeRow(
    student: StudentDto,
    letter: String,
    letters: List<String>,
    enabled: Boolean,
    onPick: (String?) -> Unit,
) {
    var open by remember { mutableStateOf(false) }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        RollText(student)
        StudentLabel(student, Modifier.weight(1f))
        Box {
            OutlinedButton(
                onClick = { open = true },
                enabled = enabled,
                contentPadding = PaddingValues(horizontal = 12.dp),
                modifier = Modifier.width(96.dp)
            ) {
                Text(letter.ifBlank { "—" }, fontWeight = if (letter.isBlank()) FontWeight.Normal else FontWeight.Bold)
                Icon(Icons.Default.ArrowDropDown, contentDescription = "Pick grade")
            }
            DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
                DropdownMenuItem(text = { Text("— (not graded)") }, onClick = { open = false; onPick(null) })
                letters.forEach { g ->
                    DropdownMenuItem(text = { Text(g) }, onClick = { open = false; onPick(g) })
                }
            }
        }
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
