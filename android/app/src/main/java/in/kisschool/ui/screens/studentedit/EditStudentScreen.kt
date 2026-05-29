package `in`.kisschool.ui.screens.studentedit

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import coil.compose.AsyncImage
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.DateField
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun EditStudentScreen(
    vm: EditStudentViewModel,
    onSaved: (queued: Boolean) -> Unit,
    onBack: () -> Unit,
) {
    val s by vm.state.collectAsStateWithLifecycle()
    val scroll = rememberScrollState()

    LaunchedEffect(s.done) {
        if (s.done) onSaved(s.queued)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Edit student") },
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
                .verticalScroll(scroll)
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            when {
                s.loading -> LoadingRow()
                s.loadError != null -> ErrorBanner(s.loadError)
                else -> {
                    val f = s.form
                    val err = s.errors

                    // ── Academic ───────────────────────────────────────────
                    SectionCard("Academic") {
                        ClassDropdown(
                            classes = s.classOptions,
                            selected = f.className.ifBlank { null },
                            onSelect = { v -> vm.update { it.copy(className = v) } },
                            label = "Class",
                            modifier = Modifier.fillMaxWidth()
                        )
                        FieldError(err["class_name"])
                        FormField(
                            label = "Admission no",
                            value = f.admissionNo,
                            onChange = { v -> vm.update { it.copy(admissionNo = digitsOnly(v)) } },
                            error = err["admission_no"],
                            keyboard = KeyboardType.Number
                        )
                        FormField(
                            label = "Roll no",
                            value = f.rollNo,
                            onChange = { v -> vm.update { it.copy(rollNo = v) } },
                            error = err["roll_no"]
                        )
                    }

                    // ── Profile ────────────────────────────────────────────
                    SectionCard("Profile") {
                        FormField(
                            label = "Student name",
                            value = f.name,
                            onChange = { v -> vm.update { it.copy(name = v) } },
                            error = err["name"],
                            capitalizeWords = true
                        )
                        FormField(
                            label = "Father's name",
                            value = f.father,
                            onChange = { v -> vm.update { it.copy(father = v) } },
                            error = err["father"],
                            capitalizeWords = true
                        )
                        FormField(
                            label = "Mother's name",
                            value = f.mother,
                            onChange = { v -> vm.update { it.copy(mother = v) } },
                            error = err["mother"],
                            capitalizeWords = true
                        )
                        ClassDropdown(
                            classes = GENDERS,
                            selected = f.gender.ifBlank { null },
                            onSelect = { v -> vm.update { it.copy(gender = v) } },
                            label = "Gender",
                            modifier = Modifier.fillMaxWidth()
                        )
                        FieldError(err["gender"])
                        DateField(
                            isoDate = f.dob,
                            onDateChange = { v -> vm.update { it.copy(dob = v) } },
                            label = "Date of birth",
                            modifier = Modifier.fillMaxWidth()
                        )
                        FieldError(err["dob"])
                        ClassDropdown(
                            classes = RELIGIONS,
                            selected = f.religion.ifBlank { null },
                            onSelect = { v -> vm.update { it.copy(religion = v) } },
                            label = "Religion (optional)",
                            modifier = Modifier.fillMaxWidth()
                        )
                    }

                    // ── Contact ────────────────────────────────────────────
                    SectionCard("Contact") {
                        FormField(
                            label = "Phone",
                            value = f.phone,
                            onChange = { v -> vm.update { it.copy(phone = digitsOnly(v).take(10)) } },
                            error = err["phone"],
                            keyboard = KeyboardType.Phone
                        )
                        FormField(
                            label = "Alternate phone (optional)",
                            value = f.altPhone,
                            onChange = { v -> vm.update { it.copy(altPhone = digitsOnly(v).take(10)) } },
                            error = err["alt_phone"],
                            keyboard = KeyboardType.Phone
                        )
                        FormField(
                            label = "Aadhaar",
                            value = f.aadhar,
                            onChange = { v -> vm.update { it.copy(aadhar = digitsOnly(v).take(12)) } },
                            error = err["aadhar"],
                            keyboard = KeyboardType.Number
                        )
                        FormField(
                            label = "Village (optional)",
                            value = f.village,
                            onChange = { v -> vm.update { it.copy(village = v) } }
                        )
                        FormField(
                            label = "Previous school (optional)",
                            value = f.prevSchool,
                            onChange = { v -> vm.update { it.copy(prevSchool = v) } }
                        )
                    }

                    // ── Bank & fee (optional) ──────────────────────────────
                    SectionCard("Bank & fee (optional)") {
                        FormField(
                            label = "Bank name",
                            value = f.bankName,
                            onChange = { v -> vm.update { it.copy(bankName = v) } }
                        )
                        FormField(
                            label = "Bank account no",
                            value = f.bankAcc,
                            onChange = { v -> vm.update { it.copy(bankAcc = digitsOnly(v)) } },
                            keyboard = KeyboardType.Number
                        )
                        FormField(
                            label = "IFSC",
                            value = f.bankIfsc,
                            onChange = { v -> vm.update { it.copy(bankIfsc = v.uppercase()) } }
                        )
                        FormField(
                            label = "Annual fee (₹)",
                            value = f.annualFee,
                            onChange = { v -> vm.update { it.copy(annualFee = digitsOnly(v)) } },
                            keyboard = KeyboardType.Number
                        )
                    }

                    // ── Documents ──────────────────────────────────────────
                    SectionCard("Documents") {
                        Text(
                            "Photos & certificates save immediately (they don't go through the edit-approval step).",
                            style = MaterialTheme.typography.labelSmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                        DocSlot("Student photo", "photo", s.hasPhoto, vm.documentUrl("photo"),
                            s.uploadingKind == "photo", vm::uploadDocument)
                        DocSlot("DOB certificate", "dob_cert", s.hasDobCert, vm.documentUrl("dob_cert"),
                            s.uploadingKind == "dob_cert", vm::uploadDocument)
                        DocSlot("Aadhaar document", "aadhar", s.hasAadhar, vm.documentUrl("aadhar"),
                            s.uploadingKind == "aadhar", vm::uploadDocument)
                        ErrorBanner(s.docError)
                        s.docMessage?.let {
                            Text(it, style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.primary)
                        }
                    }

                    ErrorBanner(s.saveError)

                    Button(
                        onClick = vm::save,
                        enabled = !s.saving,
                        modifier = Modifier.fillMaxWidth().height(52.dp)
                    ) {
                        if (s.saving) CircularProgressIndicator(
                            strokeWidth = 2.dp,
                            modifier = Modifier.height(20.dp)
                        ) else Text("Save changes")
                    }

                    Text(
                        "Edits made by staff are sent to a super-admin for approval before they take effect.",
                        style = MaterialTheme.typography.labelSmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
        }
    }
}

@Composable
private fun DocSlot(
    label: String,
    kind: String,
    present: Boolean,
    imageUrl: String?,
    uploading: Boolean,
    onUpload: (kind: String, bytes: ByteArray, mime: String) -> Unit,
) {
    val ctx = LocalContext.current
    val picker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri ->
        if (uri != null) {
            val mime = ctx.contentResolver.getType(uri) ?: "image/jpeg"
            val bytes = runCatching { ctx.contentResolver.openInputStream(uri)?.use { it.readBytes() } }.getOrNull()
            if (bytes != null && bytes.isNotEmpty()) onUpload(kind, bytes, mime)
        }
    }
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        // Thumbnail (photo) or a status box for cert/aadhar.
        if (imageUrl != null) {
            AsyncImage(
                model = imageUrl,
                contentDescription = label,
                contentScale = ContentScale.Crop,
                modifier = Modifier
                    .size(56.dp)
                    .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp))
            )
        } else {
            Box(
                Modifier
                    .size(56.dp)
                    .background(MaterialTheme.colorScheme.surfaceVariant, RoundedCornerShape(8.dp)),
                contentAlignment = Alignment.Center
            ) {
                Text(if (present) "✓" else "—", color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        Column(Modifier.weight(1f).padding(horizontal = 12.dp)) {
            Text(label, fontWeight = FontWeight.Medium)
            Text(
                if (present) "Uploaded" else "Not uploaded",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        OutlinedButton(onClick = { picker.launch("image/*") }, enabled = !uploading) {
            if (uploading) {
                CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
            } else {
                Text(if (present) "Replace" else "Upload")
            }
        }
    }
}

@Composable
private fun SectionCard(title: String, content: @Composable () -> Unit) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(
                title,
                style = MaterialTheme.typography.titleSmall,
                color = MaterialTheme.colorScheme.primary
            )
            content()
        }
    }
}

@Composable
private fun FormField(
    label: String,
    value: String,
    onChange: (String) -> Unit,
    error: String? = null,
    keyboard: KeyboardType = KeyboardType.Text,
    capitalizeWords: Boolean = false,
) {
    OutlinedTextField(
        value = value,
        onValueChange = onChange,
        label = { Text(label) },
        singleLine = true,
        isError = error != null,
        supportingText = if (error != null) {
            { Text(error) }
        } else null,
        keyboardOptions = KeyboardOptions(
            keyboardType = keyboard,
            capitalization = if (capitalizeWords) KeyboardCapitalization.Words else KeyboardCapitalization.None
        ),
        modifier = Modifier.fillMaxWidth()
    )
}

/** Inline error line for the dropdown/date fields (which have no supportingText slot). */
@Composable
private fun FieldError(error: String?) {
    if (error.isNullOrBlank()) return
    Text(
        error,
        style = MaterialTheme.typography.labelSmall,
        color = MaterialTheme.colorScheme.error,
        modifier = Modifier.padding(start = 4.dp)
    )
}
