package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.BatchDetailDto
import `in`.kisschool.data.api.dto.BatchSaveBody
import `in`.kisschool.data.api.dto.ClassSubjectDetailDto
import `in`.kisschool.data.api.dto.ClassSubjectDto
import `in`.kisschool.data.api.dto.RequestEditBody
import org.json.JSONObject
import retrofit2.Response

class MarksRepository(private val api: ApiService) {

    /** Academic subjects for a class (excludes the "grading" category, like the web). */
    suspend fun subjects(className: String): List<ClassSubjectDto> =
        api.classSubjects(className)
            .filter { it.category != "grading" }
            .sortedBy { it.orderIndex }

    suspend fun subjectDetail(subjectId: Long): ClassSubjectDetailDto =
        api.classSubjectDetail(subjectId)

    /** Load the batch for the (class, subject, exam_type, session) tuple, or null. */
    suspend fun getBatch(
        className: String, subject: String, examType: String, session: String
    ): BatchDetailDto? {
        val resp = api.getMarksBatch(className, subject, examType, session)
        if (resp.isSuccessful) return resp.body() // body is null when no batch exists
        throw RuntimeException(detailOf(resp) ?: "Failed to load batch (HTTP ${resp.code()})")
    }

    suspend fun saveBatch(body: BatchSaveBody): BatchDetailDto {
        val resp = api.saveMarksBatch(body)
        if (resp.isSuccessful) return resp.body() ?: throw RuntimeException("Empty response")
        throw RuntimeException(detailOf(resp) ?: "Save failed (HTTP ${resp.code()})")
    }

    suspend fun submit(batchId: Long): BatchDetailDto {
        val resp = api.submitMarksBatch(batchId)
        if (resp.isSuccessful) return resp.body() ?: throw RuntimeException("Empty response")
        throw RuntimeException(detailOf(resp) ?: "Submit failed (HTTP ${resp.code()})")
    }

    suspend fun requestEdit(batchId: Long, reason: String) {
        val resp = api.requestMarksEdit(batchId, RequestEditBody(reason))
        if (!resp.isSuccessful) {
            throw RuntimeException(detailOf(resp) ?: "Request failed (HTTP ${resp.code()})")
        }
    }

    /** FastAPI `detail` may be a plain string OR an object `{message, rows}` (the
     *  out-of-range validation error) — surface a readable message for either. */
    private fun detailOf(resp: Response<*>): String? {
        val raw = resp.errorBody()?.string() ?: return null
        return try {
            val root = JSONObject(raw)
            val d = root.opt("detail")
            when (d) {
                is JSONObject -> d.optString("message").ifBlank { d.toString() }
                is String -> d.ifBlank { null }
                null -> null
                else -> d.toString()
            }
        } catch (_: Exception) {
            null
        }
    }
}
