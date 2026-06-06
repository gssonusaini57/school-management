package `in`.kisschool.ui.screens.students

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.EmptyState
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun StudentsScreen(
    vm: StudentsViewModel,
    onOpenStudent: (Long) -> Unit,
    onBack: () -> Unit
) {
    val s by vm.state.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Students") },
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
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            ClassDropdown(
                classes = s.allowedClasses,
                selected = s.selectedClass,
                onSelect = vm::selectClass
            )

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
                        Card(onClick = { onOpenStudent(student.id) }) {
                            androidx.compose.foundation.layout.Row(
                                Modifier.fillMaxWidth().padding(16.dp),
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text(student.name, style = MaterialTheme.typography.titleMedium)
                                    Text(
                                        student.className,
                                        style = MaterialTheme.typography.bodySmall,
                                        color = MaterialTheme.colorScheme.onSurfaceVariant
                                    )
                                    if (student.hasPendingEdit) {
                                        Text(
                                            "Pending approval",
                                            style = MaterialTheme.typography.labelSmall,
                                            color = MaterialTheme.colorScheme.onTertiaryContainer,
                                            modifier = Modifier
                                                .padding(top = 4.dp)
                                                .background(
                                                    MaterialTheme.colorScheme.tertiaryContainer,
                                                    RoundedCornerShape(4.dp)
                                                )
                                                .padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                }
                                Icon(
                                    Icons.AutoMirrored.Filled.KeyboardArrowRight,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}
