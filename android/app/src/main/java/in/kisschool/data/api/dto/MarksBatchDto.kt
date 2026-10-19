package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * One student's entry in a save payload: `marks` for a numeric exam component, or
 * `grade` (a letter such as "A2") for a graded component (max_marks 0). Set exactly
 * one of the two, by name.
 *
 * The unset one is left out of the JSON entirely, because the app's Gson
 * (GsonConverterFactory.create() in AppContainer) does not serialize nulls:
 * a numeric item goes out as {"student_id":7,"marks":45} and a graded one as
 * {"student_id":7,"grade":"A2"}. The server tolerates a missing key; it rejects a
 * numeric item without marks and a graded item without a grade. Do not turn on
 * serializeNulls() for that Gson without revisiting this.
 */
data class MarkItemIn(
    @SerializedName("student_id") val studentId: Long,
    val marks: Int? = null,
    val grade: String? = null,
)

/** One saved row returned in a batch. */
data class MarkItemOut(
    val id: Long,
    @SerializedName("student_id") val studentId: Long,
    /** Always present; the server stores 0 for a graded component. */
    val marks: Int,
    /** The letter for a graded component; null for numeric marks and on older servers. */
    val grade: String? = null,
)

/** POST /marks/batches body — upsert a batch + its scored rows. */
data class BatchSaveBody(
    @SerializedName("class_name") val className: String,
    val subject: String,
    @SerializedName("exam_type") val examType: String,
    val session: String,
    @SerializedName("max_marks") val maxMarks: Int,
    val items: List<MarkItemIn>,
    /**
     * The batch id this screen loaded before the edit, or 0 when the test had no
     * saved marks. The server refuses the save (409) when its batch for the test is
     * a different one, so a stale screen can't overwrite or prune saved marks.
     * Never null: the app's Gson drops nulls, and an absent field skips the check.
     * Servers older than the check ignore the field.
     */
    @SerializedName("base_batch_id") val baseBatchId: Long = 0,
    /**
     * The [BatchDetailDto.revision] this screen loaded or last saved, so a screen left
     * open can't save over marks saved meanwhile from the web or another phone (409).
     * Null when the test had no saved marks: Gson drops it and the server checks only
     * [baseBatchId]. Servers older than the check ignore the field.
     */
    @SerializedName("base_revision") val baseRevision: Int? = null,
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
    /**
     * Goes up on every change to the batch's marks or status; sent back as
     * [BatchSaveBody.baseRevision]. Older servers leave it out (0).
     */
    val revision: Int = 0,
    val items: List<MarkItemOut> = emptyList(),
    @SerializedName("pending_edit_request_id") val pendingEditRequestId: Long? = null,
    @SerializedName("last_rejection") val lastRejection: String? = null,
)

/** POST /marks/batches/{id}/request-edit body — reason is required (1–2000). */
data class RequestEditBody(
    val reason: String,
)
