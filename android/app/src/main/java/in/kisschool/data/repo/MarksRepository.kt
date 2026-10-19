package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.BatchDetailDto
import `in`.kisschool.data.api.dto.BatchSaveBody
import `in`.kisschool.data.api.dto.ClassSubjectDetailDto
import `in`.kisschool.data.api.dto.ClassSubjectDto
import `in`.kisschool.data.api.dto.RequestEditBody
import `in`.kisschool.data.api.dto.SubjectEnrollmentsDto

class MarksRepository(private val api: ApiService) {

    /**
     * Every subject of a class, in display order. Graded subjects (Computer, P.E., …)
     * are included: their exam components have max 0 and take a letter grade.
     */
    suspend fun subjects(className: String): List<ClassSubjectDto> =
        api.classSubjects(className).sortedBy { it.orderIndex }

    suspend fun subjectDetail(subjectId: Long): ClassSubjectDetailDto =
        api.classSubjectDetail(subjectId)

    /** Who takes a subject now; only asked for an optional subject (the server is new enough). */
    suspend fun enrollments(subjectId: Long): SubjectEnrollmentsDto =
        api.subjectEnrollments(subjectId)

    /** Load the batch for the (class, subject, exam_type, session) tuple, or null. */
    suspend fun getBatch(
        className: String, subject: String, examType: String, session: String
    ): BatchDetailDto? {
        val resp = api.getMarksBatch(className, subject, examType, session)
        if (resp.isSuccessful) return resp.body() // body is null when no batch exists
        throw ApiException(resp.apiError().message ?: "Failed to load batch (HTTP ${resp.code()})", resp.code())
    }

    suspend fun saveBatch(body: BatchSaveBody): BatchDetailDto {
        val resp = api.saveMarksBatch(body)
        if (resp.isSuccessful) return resp.body() ?: throw ApiException("Empty response")
        val err = resp.apiError()
        // A server from before letter grades rejects max 0 / items without marks
        // with a request-validation list; say so instead of "Field required".
        if (resp.code() == 422 && err.validation && body.maxMarks == 0) {
            throw ApiException("This server can't save letter grades yet. It needs the latest update.", 422)
        }
        throw ApiException(err.message ?: "Save failed (HTTP ${resp.code()})", resp.code())
    }

    suspend fun submit(batchId: Long): BatchDetailDto {
        val resp = api.submitMarksBatch(batchId)
        if (resp.isSuccessful) return resp.body() ?: throw ApiException("Empty response")
        throw ApiException(resp.apiError().message ?: "Submit failed (HTTP ${resp.code()})", resp.code())
    }

    suspend fun requestEdit(batchId: Long, reason: String) {
        val resp = api.requestMarksEdit(batchId, RequestEditBody(reason))
        if (!resp.isSuccessful) {
            throw ApiException(resp.apiError().message ?: "Request failed (HTTP ${resp.code()})", resp.code())
        }
    }
}
