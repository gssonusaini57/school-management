package `in`.kisschool.data.api

import `in`.kisschool.data.api.dto.AttendanceDto
import `in`.kisschool.data.api.dto.ChangePasswordRequest
import `in`.kisschool.data.api.dto.LoginRequest
import `in`.kisschool.data.api.dto.LoginResponse
import `in`.kisschool.data.api.dto.BatchDetailDto
import `in`.kisschool.data.api.dto.BatchSaveBody
import `in`.kisschool.data.api.dto.ClassSubjectDetailDto
import `in`.kisschool.data.api.dto.ClassSubjectDto
import `in`.kisschool.data.api.dto.MeResponse
import `in`.kisschool.data.api.dto.RequestEditBody
import `in`.kisschool.data.api.dto.StudentDto
import `in`.kisschool.data.api.dto.StudentPageDto
import `in`.kisschool.data.api.dto.StudentUpdateDto
import okhttp3.MultipartBody
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

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

    @PATCH("students/{id}")
    suspend fun updateStudent(
        @Path("id") id: Long,
        @Body body: StudentUpdateDto
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

    @POST("staff/change-password")
    suspend fun changeStaffPassword(@Body body: ChangePasswordRequest): Response<Unit>
}
