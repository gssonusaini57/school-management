package `in`.kisschool.ui.screens.attendance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.EmptyState
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import `in`.kisschool.ui.components.StatusChip
import `in`.kisschool.ui.components.todayIso

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun AttendanceScreen(vm: AttendanceViewModel, onBack: () -> Unit) {
    val s by vm.state.collectAsStateWithLifecycle()
    val snackbar = remember { SnackbarHostState() }

    LaunchedEffect(s.savedAt) {
        if (s.savedAt > 0L) snackbar.showSnackbar("Attendance saved")
    }

    LaunchedEffect(Unit) {
        val today = todayIso()
        if (s.date != today) vm.selectDate(today)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Take attendance") },
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
        },
        snackbarHost = { SnackbarHost(snackbar) }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(
                Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                ClassDropdown(
                    classes = s.allowedClasses,
                    selected = s.selectedClass,
                    onSelect = vm::selectClass,
                    modifier = Modifier.weight(1f)
                )
                Column(Modifier.weight(1f)) {
                    Text(
                        "Date",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text(
                        "Today (${s.date})",
                        style = MaterialTheme.typography.bodyLarge
                    )
                }
            }

            ErrorBanner(s.error)

            HorizontalDivider()

            when {
                s.loading -> LoadingRow()
                s.selectedClass == null -> EmptyState("No class selected.")
                s.students.isEmpty() -> EmptyState("No students in this class yet.")
                else -> LazyColumn(
                    Modifier.weight(1f),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(s.students, key = { it.id }) { student ->
                        val current = s.statuses[student.id] ?: "P"
                        Row(
                            Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Text(
                                student.name,
                                modifier = Modifier.weight(1f),
                                style = MaterialTheme.typography.bodyLarge
                            )
                            StatusChip("P", Color(0xFF16A34A), current == "P") { vm.setStatus(student.id, "P") }
                            Spacer(Modifier.width(6.dp))
                            StatusChip("A", Color(0xFFDC2626), current == "A") { vm.setStatus(student.id, "A") }
                            Spacer(Modifier.width(6.dp))
                            StatusChip("L", Color(0xFFD97706), current == "L") { vm.setStatus(student.id, "L") }
                        }
                    }
                }
            }

            Button(
                onClick = vm::save,
                enabled = !s.saving && !s.loading && s.students.isNotEmpty(),
                modifier = Modifier.fillMaxWidth().height(52.dp)
            ) {
                if (s.saving) CircularProgressIndicator(
                    strokeWidth = 2.dp,
                    modifier = Modifier.height(20.dp)
                )
                else Text("Save attendance")
            }
        }
    }
}

