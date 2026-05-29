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
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.Card
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
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
    onBack: () -> Unit,
) {
    val s by vm.state.collectAsStateWithLifecycle()
    val scroll = rememberScrollState()
    val student = s.student
    val pending = student?.pendingEditRequestId != null

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
                    // Edit is disabled while an edit request is awaiting super-admin approval.
                    if (student != null) {
                        IconButton(onClick = onEdit, enabled = !pending) {
                            Icon(Icons.Default.Edit, contentDescription = "Edit student")
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
                    if (pending) PendingBanner(student.pendingEditRequestedAt)
                    StudentBody(student)
                }
            }
        }
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
