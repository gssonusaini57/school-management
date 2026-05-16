package com.expressonly.kisattendance.data.api

import com.expressonly.kisattendance.data.api.dto.AttendanceDto
import com.expressonly.kisattendance.data.api.dto.ChangePasswordRequest
import com.expressonly.kisattendance.data.api.dto.LoginRequest
import com.expressonly.kisattendance.data.api.dto.LoginResponse
import com.expressonly.kisattendance.data.api.dto.MeResponse
import com.expressonly.kisattendance.data.api.dto.StudentDto
import retrofit2.Response
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.PUT
import retrofit2.http.Query

interface ApiService {

    @POST("auth/login")
    suspend fun login(@Body body: LoginRequest): LoginResponse

    @GET("auth/me")
    suspend fun me(): MeResponse

    @GET("students")
    suspend fun students(@Query("class") className: String): List<StudentDto>

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
