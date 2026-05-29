package `in`.kisschool.ui.screens.studentedit

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import `in`.kisschool.BuildConfig
import `in`.kisschool.data.repo.StudentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class EditStudentUiState(
    val loading: Boolean = true,
    val form: StudentForm = StudentForm(),
    val errors: Map<String, String> = emptyMap(),
    val loadError: String? = null,
    val saving: Boolean = false,
    val saveError: String? = null,
    val done: Boolean = false,
    /** True when the save was queued for super-admin approval (staff path). */
    val queued: Boolean = false,
    /** The class dropdown options for this user (their allowed classes, else all). */
    val classOptions: List<String> = CLASSES,
    // ── Documents (photo / dob_cert / aadhar) ───────────────────────────────
    val hasPhoto: Boolean = false,
    val hasDobCert: Boolean = false,
    val hasAadhar: Boolean = false,
    val docVersion: Int = 0,           // bumps after an upload to bust the image cache
    val uploadingKind: String? = null, // which doc is currently uploading
    val docError: String? = null,
    val docMessage: String? = null,
)

class EditStudentViewModel(
    private val studentRepo: StudentRepository,
    private val studentId: Long,
    private val allowedClasses: List<String>,
    private val authToken: String?,
) : ViewModel() {

    private val _state = MutableStateFlow(EditStudentUiState())
    val state: StateFlow<EditStudentUiState> = _state.asStateFlow()

    init {
        _state.value = _state.value.copy(
            classOptions = if (allowedClasses.isNotEmpty()) allowedClasses else CLASSES
        )
        load()
    }

    /** Staff have no GET /students/{id}; fetch by their allowed classes and match. */
    private fun load() {
        viewModelScope.launch {
            try {
                val classes = allowedClasses.ifEmpty { CLASSES }
                for (cls in classes) {
                    val match = studentRepo.byClass(cls).firstOrNull { it.id == studentId }
                    if (match != null) {
                        _state.value = _state.value.copy(
                            loading = false,
                            form = match.toForm(),
                            hasPhoto = match.hasPhoto,
                            hasDobCert = match.hasDobCert,
                            hasAadhar = match.hasAadhar,
                        )
                        return@launch
                    }
                }
                _state.value = _state.value.copy(loading = false, loadError = "Student not found")
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    loading = false,
                    loadError = e.message ?: "Failed to load student"
                )
            }
        }
    }

    /** Authenticated inline URL for a document (token in query), or null if absent. */
    fun documentUrl(kind: String): String? {
        val present = when (kind) {
            "photo" -> _state.value.hasPhoto
            "dob_cert" -> _state.value.hasDobCert
            "aadhar" -> _state.value.hasAadhar
            else -> false
        }
        if (!present || authToken.isNullOrBlank()) return null
        return "${BuildConfig.API_BASE_URL}files/students/$studentId/$kind/inline" +
            "?token=$authToken&v=${_state.value.docVersion}"
    }

    fun uploadDocument(kind: String, bytes: ByteArray, mime: String) {
        _state.value = _state.value.copy(uploadingKind = kind, docError = null, docMessage = null)
        viewModelScope.launch {
            try {
                studentRepo.uploadDocument(studentId, kind, bytes, mime, "$kind-upload")
                _state.value = _state.value.copy(
                    uploadingKind = null,
                    docVersion = _state.value.docVersion + 1,
                    hasPhoto = if (kind == "photo") true else _state.value.hasPhoto,
                    hasDobCert = if (kind == "dob_cert") true else _state.value.hasDobCert,
                    hasAadhar = if (kind == "aadhar") true else _state.value.hasAadhar,
                    docMessage = "Document uploaded",
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    uploadingKind = null,
                    docError = e.message ?: "Upload failed",
                )
            }
        }
    }

    /** Update a single field; clears that field's error and any prior save error. */
    fun update(transform: (StudentForm) -> StudentForm) {
        _state.value = _state.value.copy(form = transform(_state.value.form), saveError = null)
    }

    fun save() {
        val form = _state.value.form
        val errors = form.validate()
        if (errors.isNotEmpty()) {
            _state.value = _state.value.copy(errors = errors, saveError = "Please fix the highlighted fields")
            return
        }
        _state.value = _state.value.copy(saving = true, errors = emptyMap(), saveError = null)
        viewModelScope.launch {
            try {
                val updated = studentRepo.update(studentId, form.toUpdateDto())
                _state.value = _state.value.copy(
                    saving = false,
                    done = true,
                    queued = updated.pendingEditRequestId != null
                )
            } catch (e: Exception) {
                _state.value = _state.value.copy(
                    saving = false,
                    saveError = e.message ?: "Save failed"
                )
            }
        }
    }
}
