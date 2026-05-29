package `in`.kisschool.data.api.dto

/** Paginated list wrapper returned by GET /students (and other list endpoints). */
data class StudentPageDto(
    val items: List<StudentDto> = emptyList(),
    val total: Int = 0,
    val page: Int = 1,
    @com.google.gson.annotations.SerializedName("page_size") val pageSize: Int = 0,
)
