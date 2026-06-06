package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/** One field's before→after for a student edit request. Values are Any? because
 *  Gson decodes JSON scalars as String/Double/Boolean/null (see diffValue in the UI). */
data class DiffPair(val old: Any? = null, val new: Any? = null)

data class EditRequestDto(
    val id: Long,
    @SerializedName("student_id") val studentId: Long = 0,
    @SerializedName("student_name") val studentName: String = "",
    @SerializedName("class_name") val className: String? = null,
    @SerializedName("requested_at") val requestedAt: String? = null,
    @SerializedName("requested_by") val requestedBy: String? = null,
    @SerializedName("requested_by_role") val requestedByRole: String? = null,
    val changes: Map<String, DiffPair> = emptyMap(),
    val status: String = "pending",
)

data class EditRequestListDto(val items: List<EditRequestDto> = emptyList())

data class MarksEditRequestDto(
    val id: Long,
    @SerializedName("batch_id") val batchId: Long = 0,
    @SerializedName("class_name") val className: String = "",
    val subject: String = "",
    @SerializedName("exam_type") val examType: String = "",
    val session: String = "",
    @SerializedName("student_count") val studentCount: Int = 0,
    @SerializedName("requested_at") val requestedAt: String? = null,
    @SerializedName("requested_by") val requestedBy: String? = null,
    val reason: String? = null,
    val status: String = "pending",
)

data class MarksEditRequestListDto(val items: List<MarksEditRequestDto> = emptyList())

data class DeletionRequestDto(
    val kind: String,            // "student" | "staff"
    val id: Long,
    val name: String = "",
    @SerializedName("class_name") val className: String? = null,
    val designation: String? = null,
    val status: String = "",     // "pending_delete" | "deleted"
    @SerializedName("delete_requested_by") val deleteRequestedBy: String? = null,
    @SerializedName("delete_reason") val deleteReason: String? = null,
)

data class DeletionRequestListDto(val items: List<DeletionRequestDto> = emptyList())

/** Optional reason for reject endpoints. */
data class RejectBody(val reason: String? = null)
