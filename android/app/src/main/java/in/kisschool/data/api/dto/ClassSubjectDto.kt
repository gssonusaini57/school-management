package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/*
 * Every constructor parameter of these classes has a default on purpose (as in
 * ResultsDto.kt): Kotlin then emits a no-arg constructor, Gson builds the object
 * through it, and a key an older server leaves out (is_optional and
 * enrolled_student_ids before the optional-subjects update) keeps its default
 * here. Without it Gson skips the constructor and the field would be null.
 */

/** GET /class-subjects?class= — one per (class, subject). */
data class ClassSubjectDto(
    val id: Long = 0,
    @SerializedName("class_name") val className: String = "",
    @SerializedName("subject_name") val subjectName: String = "",
    @SerializedName("subject_name_pa") val subjectNamePa: String? = null,
    val category: String = "",            // academic | co_curricular | grading
    @SerializedName("order_index") val orderIndex: Int = 0,
    /**
     * An optional (additional) subject, such as Mathematics in 11th and 12th: only the
     * students in [enrolledStudentIds] take it, and only they get marks for it.
     */
    @SerializedName("is_optional") val isOptional: Boolean = false,
    /**
     * Sorted ids of the students who take the subject (active students of its class).
     * Sent whether or not the subject is optional; only an optional subject uses them.
     */
    @SerializedName("enrolled_student_ids") val enrolledStudentIds: List<Long> = emptyList(),
)

/**
 * An exam component within a subject (e.g. "P.T. First", max 35). `maxMarks == 0`
 * marks a graded exam ("Term 1 Grade") that takes a letter instead of marks.
 */
data class ExamComponentDto(
    val id: Long,
    @SerializedName("class_subject_id") val classSubjectId: Long,
    @SerializedName("component_name") val componentName: String,
    @SerializedName("max_marks") val maxMarks: Int,
    @SerializedName("order_index") val orderIndex: Int = 0,
    /** 1 | 2, or null when the component counts in both terms (and on older servers). */
    val term: Int? = null,
)

/** GET /class-subjects/{id} — subject plus its exam components, and who takes it. */
data class ClassSubjectDetailDto(
    val id: Long = 0,
    @SerializedName("class_name") val className: String = "",
    @SerializedName("subject_name") val subjectName: String = "",
    val category: String = "",
    val components: List<ExamComponentDto> = emptyList(),
    /** As on [ClassSubjectDto]. */
    @SerializedName("is_optional") val isOptional: Boolean = false,
    @SerializedName("enrolled_student_ids") val enrolledStudentIds: List<Long> = emptyList(),
)

/** GET /class-subjects/{id}/enrollments — who takes a subject now. */
data class SubjectEnrollmentsDto(
    @SerializedName("class_subject_id") val classSubjectId: Long = 0,
    @SerializedName("class_name") val className: String = "",
    @SerializedName("subject_name") val subjectName: String = "",
    @SerializedName("is_optional") val isOptional: Boolean = false,
    /** Sorted ids, as [ClassSubjectDto.enrolledStudentIds]. */
    @SerializedName("student_ids") val studentIds: List<Long> = emptyList(),
)
