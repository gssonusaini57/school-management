package com.expressonly.kisattendance.data.repo

import com.expressonly.kisattendance.data.api.ApiService
import com.expressonly.kisattendance.data.api.dto.StudentDto

class StudentRepository(private val api: ApiService) {
    suspend fun byClass(className: String): List<StudentDto> =
        api.students(className).sortedBy { it.name.lowercase() }
}
