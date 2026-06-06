package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.DeletionRequestDto
import `in`.kisschool.data.api.dto.EditRequestDto
import `in`.kisschool.data.api.dto.MarksEditRequestDto
import `in`.kisschool.data.api.dto.RejectBody
import org.json.JSONObject
import retrofit2.Response

/**
 * Approval-portal calls for admin/super-admin. List calls let Retrofit throw on
 * non-2xx (caught by the ViewModel); action calls surface the FastAPI `detail`
 * verbatim so a super-only 403 reads clearly when an admin tries to approve.
 */
class AdminRepository(private val api: ApiService) {

    suspend fun editRequests(): List<EditRequestDto> = api.editRequests().items
    suspend fun marksEditRequests(): List<MarksEditRequestDto> = api.marksEditRequests().items
    suspend fun deletionRequests(): List<DeletionRequestDto> = api.deletionRequests(null).items

    suspend fun approveEdit(id: Long) = check(api.approveEditRequest(id))
    suspend fun rejectEdit(id: Long, reason: String?) =
        check(api.rejectEditRequest(id, RejectBody(reason?.trim()?.ifBlank { null })))

    suspend fun approveMarksEdit(id: Long) = check(api.approveMarksEditRequest(id))
    suspend fun rejectMarksEdit(id: Long, reason: String?) =
        check(api.rejectMarksEditRequest(id, RejectBody(reason?.trim()?.ifBlank { null })))

    suspend fun approveDeletion(kind: String, id: Long) = check(api.approveDeletion(kind, id))
    suspend fun restoreDeletion(kind: String, id: Long) = check(api.restoreDeletion(kind, id))
    suspend fun purgeDeletion(kind: String, id: Long) = check(api.purgeDeletion(kind, id))

    private fun check(resp: Response<Unit>) {
        if (resp.isSuccessful) return
        val detail = resp.errorBody()?.string()?.let { raw ->
            try { JSONObject(raw).optString("detail").ifBlank { null } } catch (_: Exception) { null }
        }
        throw RuntimeException(detail ?: "Action failed (HTTP ${resp.code()})")
    }
}
