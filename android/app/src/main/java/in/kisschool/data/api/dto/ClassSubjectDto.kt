package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/** GET /class-subjects?class= — one per (class, subject). */
data class ClassSubjectDto(
    val id: Long,
    @SerializedName("class_name") val className: String,
    @SerializedName("subject_name") val subjectName: String,
    @SerializedName("subject_name_pa") val subjectNamePa: String? = null,
    val category: String,                 // academic | co_curricular | grading
    @SerializedName("order_index") val orderIndex: Int = 0,
)

/** A scored exam component within a subject (e.g. "P.T. First", max 35). */
data class ExamComponentDto(
    val id: Long,
    @SerializedName("class_subject_id") val classSubjectId: Long,
    @SerializedName("component_name") val componentName: String,
    @SerializedName("max_marks") val maxMarks: Int,
    @SerializedName("order_index") val orderIndex: Int = 0,
)

/** GET /class-subjects/{id} — subject plus its exam components. */
data class ClassSubjectDetailDto(
    val id: Long,
    @SerializedName("class_name") val className: String,
    @SerializedName("subject_name") val subjectName: String,
    val category: String,
    val components: List<ExamComponentDto> = emptyList(),
)
