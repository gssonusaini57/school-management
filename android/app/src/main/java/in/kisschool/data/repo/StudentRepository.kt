package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.api.dto.StudentUpdateDto
import okhttp3.MediaType.Companion.toMediaTypeOrNull
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class StudentRepository(private val api: ApiService) {
    suspend fun byClass(className: String): List<StudentDto> =
        api.students(className).items.sortedBy { it.name.lowercase() }

    /**
     * PATCH a student. For a staff user the server queues an edit request instead of
     * applying directly; the returned [StudentDto] then carries a non-null
     * `pendingEditRequestId`. On a non-2xx response the FastAPI `detail` message is
     * surfaced verbatim (e.g. the 409 "edit already pending" / uniqueness conflicts).
     */
    suspend fun update(id: Long, body: StudentUpdateDto): StudentDto {
        val resp = api.updateStudent(id, body)
        if (resp.isSuccessful) {
            return resp.body() ?: throw RuntimeException("Empty response from server")
        }
        val detail = resp.errorBody()?.string()?.let { raw ->
            try {
                JSONObject(raw).optString("detail").ifBlank { null }
            } catch (_: Exception) {
                null
            }
        }
        throw RuntimeException(detail ?: "Update failed (HTTP ${resp.code()})")
    }

    /** Upload (or replace) a student document. kind ∈ {photo, dob_cert, aadhar}. */
    suspend fun uploadDocument(id: Long, kind: String, bytes: ByteArray, mime: String, filename: String) {
        val body = bytes.toRequestBody(mime.toMediaTypeOrNull())
        val part = MultipartBody.Part.createFormData("file", filename, body)
        val resp = api.uploadDocument(id, kind, part)
        if (!resp.isSuccessful) {
            val detail = resp.errorBody()?.string()?.let { raw ->
                try { JSONObject(raw).optString("detail").ifBlank { null } } catch (_: Exception) { null }
            }
            throw RuntimeException(detail ?: "Upload failed (HTTP ${resp.code()})")
        }
    }
}
