package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/** One student's score in a save payload. */
data class MarkItemIn(
    @SerializedName("student_id") val studentId: Long,
    val marks: Int,
)

/** One scored row returned in a batch. */
data class MarkItemOut(
    val id: Long,
    @SerializedName("student_id") val studentId: Long,
    val marks: Int,
)

/** POST /marks/batches body — upsert a batch + its scored rows. */
data class BatchSaveBody(
    @SerializedName("class_name") val className: String,
    val subject: String,
    @SerializedName("exam_type") val examType: String,
    val session: String,
    @SerializedName("max_marks") val maxMarks: Int,
    val items: List<MarkItemIn>,
)

/** GET/POST /marks/batches response (null body from GET = no batch yet). */
data class BatchDetailDto(
    val id: Long,
    @SerializedName("class_name") val className: String,
    val subject: String,
    @SerializedName("exam_type") val examType: String,
    val session: String,
    @SerializedName("max_marks") val maxMarks: Int,
    val status: String,                    // draft | submitted
    @SerializedName("created_by") val createdBy: String? = null,
    @SerializedName("submitted_at") val submittedAt: String? = null,
    @SerializedName("submitted_by") val submittedBy: String? = null,
    val items: List<MarkItemOut> = emptyList(),
    @SerializedName("pending_edit_request_id") val pendingEditRequestId: Long? = null,
    @SerializedName("last_rejection") val lastRejection: String? = null,
)

/** POST /marks/batches/{id}/request-edit body — reason is required (1–2000). */
data class RequestEditBody(
    val reason: String,
)
