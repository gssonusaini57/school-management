package `in`.kisschool.ui.screens.studentdetail

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StudentDetailScreen(
    vm: StudentDetailViewModel,
    onEdit: () -> Unit,
    onDeleted: () -> Unit,
    onBack: () -> Unit,
) {
    val s by vm.state.collectAsStateWithLifecycle()
    val scroll = rememberScrollState()
    val student = s.student
    val pendingEdit = student?.pendingEditRequestId != null
    val pendingDelete = student?.status == "pending_delete"
    var showDeleteDialog by remember { mutableStateOf(false) }
    var navigatedAway by remember { mutableStateOf(false) }

    // On a successful delete request, leave the screen (back to the refreshed
    // list). Guard so a recomposition can't fire onDeleted() twice.
    LaunchedEffect(s.deleteRequested) {
        if (s.deleteRequested && !navigatedAway) {
            navigatedAway = true
            onDeleted()
        }
    }

    if (showDeleteDialog && student != null) {
        DeleteStudentDialog(
            studentName = student.name,
            submitting = s.deleting,
            errorText = s.deleteError,
            onDismiss = { if (!s.deleting) { showDeleteDialog = false; vm.clearDeleteError() } },
            onConfirm = { reason -> vm.requestDelete(reason) },
        )
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(student?.name ?: "Student") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    if (student != null) {
                        // Edit is disabled while an edit request is awaiting super-admin approval.
                        IconButton(onClick = onEdit, enabled = !pendingEdit) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit student")
                        }
                        // Request deletion — hidden once a deletion is already pending.
                        if (!pendingDelete) {
                            IconButton(onClick = { showDeleteDialog = true }) {
                                Icon(Icons.Default.Delete, contentDescription = "Request student deletion")
                            }
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary
                )
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(scroll)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            when {
                s.loading -> LoadingRow()
                s.error != null -> ErrorBanner(s.error)
                student != null -> {
                    if (pendingDelete) {
                        DeletePendingBanner(student.deleteReason)
                    }
                    if (pendingEdit) PendingBanner(student.pendingEditRequestedAt)
                    StudentBody(student)
                }
            }
        }
    }
}

@Composable
private fun DeleteStudentDialog(
    studentName: String,
    submitting: Boolean,
    errorText: String?,
    onDismiss: () -> Unit,
    onConfirm: (reason: String?) -> Unit,
) {
    var reason by remember { mutableStateOf("") }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Request student deletion") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    "Submit \"$studentName\" for super-admin approval. The record stays " +
                        "visible with a \"Deletion requested\" badge until it's approved.",
                    style = MaterialTheme.typography.bodyMedium,
                )
                OutlinedTextField(
                    value = reason,
                    onValueChange = { if (it.length <= 500) reason = it },
                    label = { Text("Reason (optional)") },
                    placeholder = { Text("e.g. duplicate record, left school") },
                    minLines = 2,
                    modifier = Modifier.fillMaxWidth(),
                )
                ErrorBanner(errorText)
            }
        },
        confirmButton = {
            TextButton(
                onClick = { onConfirm(reason.ifBlank { null }) },
                enabled = !submitting,
            ) {
                Text(if (submitting) "Submitting…" else "Submit request")
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !submitting) { Text("Cancel") }
        },
    )
}

@Composable
private fun DeletePendingBanner(reason: String?) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(
                MaterialTheme.colorScheme.errorContainer,
                RoundedCornerShape(8.dp)
            )
            .padding(12.dp)
    ) {
        Text(
            buildString {
                append("Deletion requested — awaiting super-admin approval.")
                if (!reason.isNullOrBlank()) append(" Reason: $reason")
            },
            color = MaterialTheme.colorScheme.onErrorContainer,
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@Composable
private fun PendingBanner(requestedAt: String?) {
    Row(
        Modifier
            .fillMaxWidth()
            .background(
                MaterialTheme.colorScheme.tertiaryContainer,
                RoundedCornerShape(8.dp)
            )
            .padding(12.dp)
    ) {
        Text(
            buildString {
                append("An edit for this student is awaiting super-admin approval.")
                if (!requestedAt.isNullOrBlank()) append(" Requested $requestedAt.")
                append(" Editing is locked until it's reviewed.")
            },
            color = MaterialTheme.colorScheme.onTertiaryContainer,
            style = MaterialTheme.typography.bodySmall
        )
    }
}

@Composable
private fun StudentBody(st: StudentDto) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(st.name, style = MaterialTheme.typography.titleLarge)
            Text(
                st.className + (st.rollNo?.let { "  ·  Roll $it" } ?: ""),
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }

    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Field("Admission no", st.admissionNo?.toString())
            Field("Admission ID", st.admissionId)
            Field("Date of birth", st.dob)
            Field("Gender", st.gender)
            Field("Religion", st.religion)
            HorizontalDivider()
            Field("Father", st.father)
            Field("Mother", st.mother)
            Field("Phone", st.phone)
            Field("Alt. phone", st.altPhone)
            Field("Aadhaar", st.aadhar)
            HorizontalDivider()
            Field("Village", st.village)
            Field("Previous school", st.prevSchool)
        }
    }
}

@Composable
private fun Field(label: String, value: String?) {
    if (value.isNullOrBlank() || value == "N/A") return
    Row(Modifier.fillMaxWidth(), verticalAlignment = androidx.compose.ui.Alignment.Top) {
        Text(
            label,
            modifier = Modifier.fillMaxWidth(0.4f),
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Text(value, fontWeight = FontWeight.Medium)
    }
}
