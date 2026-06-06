package `in`.kisschool.data.api

import `in`.kisschool.data.api.dto.AttendanceDto
import `in`.kisschool.data.api.dto.ChangePasswordRequest
import `in`.kisschool.data.api.dto.ForgotPasswordRequest
import `in`.kisschool.data.api.dto.LoginRequest
import `in`.kisschool.data.api.dto.LoginResponse
import `in`.kisschool.data.api.dto.MessageResponse
import `in`.kisschool.data.api.dto.AppVersionDto
import `in`.kisschool.data.api.dto.BatchDetailDto
import `in`.kisschool.data.api.dto.BatchSaveBody
import `in`.kisschool.data.api.dto.ClassSubjectDetailDto
import `in`.kisschool.data.api.dto.ClassSubjectDto
import `in`.kisschool.data.api.dto.DeleteStudentBody
import `in`.kisschool.data.api.dto.DeletionRequestListDto
import `in`.kisschool.data.api.dto.EditRequestListDto
import `in`.kisschool.data.api.dto.MarksEditRequestListDto
import `in`.kisschool.data.api.dto.RejectBody
import `in`.kisschool.data.api.dto.MarkedDatesDto
import `in`.kisschool.data.api.dto.MeResponse
import `in`.kisschool.data.api.dto.RequestEditBody
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.api.dto.StudentPageDto
import `in`.kisschool.data.api.dto.StudentUpdateDto
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.HTTP
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query
import retrofit2.http.Url

interface ApiService {

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("auth/me")
    suspend fun me(): MeResponse

    @GET("students")
    suspend fun students(
        @Query("class") className: String,
        @Query("page_size") pageSize: Int = 500
    ): StudentPageDto

    // Single student — returns FULL pending-edit metadata (pendingEditRequestId +
    // requester/timestamp) that the list endpoint omits. Staff-callable (scoped
    // by class on the server). Used by the detail + edit screens.
    @GET("students/{id}")
    suspend fun getStudent(@Path("id") id: Long): StudentDto

    @PATCH("students/{id}")
    suspend fun updateStudent(
        @Path("id") id: Long,
        @Body body: StudentUpdateDto
    ): Response<StudentDto>

    // Soft-delete request. Staff/admin → server flips status to `pending_delete`
    // for super-admin approval and echoes back the updated row. DELETE-with-body
    // needs @HTTP(hasBody=true); a plain @DELETE can't carry the reason payload.
    @HTTP(method = "DELETE", path = "students/{id}", hasBody = true)
    suspend fun deleteStudent(
        @Path("id") id: Long,
        @Body body: DeleteStudentBody
    ): Response<StudentDto>

    // Student documents — kind ∈ {photo, dob_cert, aadhar}. Multipart field name "file".
    @Multipart
    @POST("students/{id}/documents/{kind}")
    suspend fun uploadDocument(
        @Path("id") id: Long,
        @Path("kind") kind: String,
        @Part file: MultipartBody.Part
    ): Response<Unit>

    // ── Class subjects + exam components (Marks Entry dropdowns) ─────────────
    @GET("class-subjects")
    suspend fun classSubjects(@Query("class") className: String): List<ClassSubjectDto>

    @GET("class-subjects/{id}")
    suspend fun classSubjectDetail(@Path("id") id: Long): ClassSubjectDetailDto

    // ── Marks batches (draft → submit → lock → request-edit) ────────────────
    @GET("marks/batches")
    suspend fun getMarksBatch(
        @Query("class") className: String,
        @Query("subject") subject: String,
        @Query("exam_type") examType: String,
        @Query("session") session: String
    ): Response<BatchDetailDto>

    @POST("marks/batches")
    suspend fun saveMarksBatch(@Body body: BatchSaveBody): Response<BatchDetailDto>

    @POST("marks/batches/{id}/submit")
    suspend fun submitMarksBatch(@Path("id") id: Long): Response<BatchDetailDto>

    @POST("marks/batches/{id}/request-edit")
    suspend fun requestMarksEdit(
        @Path("id") id: Long,
        @Body body: RequestEditBody
    ): Response<Unit>

    @GET("attendance")
    suspend fun attendance(
        @Query("class") className: String,
        @Query("date") date: String
    ): Response<AttendanceDto>

    @PUT("attendance")
    suspend fun saveAttendance(@Body body: AttendanceDto): Response<Unit>

    // Clear a wrongly-marked day (removes the row + records).
    @DELETE("attendance")
    suspend fun clearAttendance(
        @Query("class") className: String,
        @Query("date") date: String,
    ): Response<Unit>

    // Dates in [from,to] that have an attendance record for this class — powers the
    // dashboard coverage calendar (one request per month vs one GET per day).
    @GET("attendance/marked-dates")
    suspend fun markedDates(
        @Query("class") className: String,
        @Query("from") from: String,
        @Query("to") to: String,
    ): MarkedDatesDto

    @POST("staff/change-password")
    suspend fun changeStaffPassword(@Body body: ChangePasswordRequest): Response<Unit>

    @POST("auth/forgot-password")
    suspend fun forgotPassword(@Body body: ForgotPasswordRequest): MessageResponse

    // Force-update manifest. Absolute @Url (it lives under /downloads/, not /api/);
    // unauthenticated + cheap so it can run before login.
    @GET
    suspend fun appVersion(@Url url: String): AppVersionDto

    // ── Approval portal (admin/super-admin) ─────────────────────────────────
    @GET("admin/edit-requests")
    suspend fun editRequests(): EditRequestListDto

    @POST("admin/edit-requests/{id}/approve")
    suspend fun approveEditRequest(@Path("id") id: Long): Response<Unit>

    @POST("admin/edit-requests/{id}/reject")
    suspend fun rejectEditRequest(@Path("id") id: Long, @Body body: RejectBody): Response<Unit>

    @GET("admin/marks-edit-requests")
    suspend fun marksEditRequests(): MarksEditRequestListDto

    @POST("admin/marks-edit-requests/{id}/approve")
    suspend fun approveMarksEditRequest(@Path("id") id: Long): Response<Unit>

    @POST("admin/marks-edit-requests/{id}/reject")
    suspend fun rejectMarksEditRequest(@Path("id") id: Long, @Body body: RejectBody): Response<Unit>

    @GET("admin/deletion-requests")
    suspend fun deletionRequests(@Query("status") status: String? = null): DeletionRequestListDto

    @POST("admin/deletion-requests/{kind}/{id}/approve")
    suspend fun approveDeletion(@Path("kind") kind: String, @Path("id") id: Long): Response<Unit>

    @POST("admin/deletion-requests/{kind}/{id}/restore")
    suspend fun restoreDeletion(@Path("kind") kind: String, @Path("id") id: Long): Response<Unit>

    @DELETE("admin/deletion-requests/{kind}/{id}")
    suspend fun purgeDeletion(@Path("kind") kind: String, @Path("id") id: Long): Response<Unit>
}
