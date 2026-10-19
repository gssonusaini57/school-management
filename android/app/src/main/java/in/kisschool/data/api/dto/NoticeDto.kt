package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * One notice from GET /notices (backend/app/schemas/notice.py NoticeOut). Every field has a
 * default, so a key an older or newer server leaves out reads as that default. Fields are
 * nullable because Gson writes an explicit JSON null straight into a field;
 * [in.kisschool.data.repo.NoticeRepository] turns this into a clean [Notice] for the UI.
 */
data class NoticeDto(
    val id: Long = 0,
    val title: String? = null,
    val content: String? = null,
    /** "normal" | "medium" | "high" (the server's Priority enum; "normal" is the default). */
    val priority: String? = null,
    val audience: String? = null,
    @SerializedName("posted_by") val postedBy: String? = null,
    /** ISO date-time; the server stores it without an offset, in UTC like its other timestamps. */
    @SerializedName("created_at") val createdAt: String? = null,
)
