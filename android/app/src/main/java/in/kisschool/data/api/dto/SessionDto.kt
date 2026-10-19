package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * One academic session (school year) and its term dates, from GET /sessions and
 * GET /sessions/current (backend/app/schemas/academic_session.py). Dates are ISO
 * yyyy-MM-dd strings. All parameters are defaulted so Gson uses the no-arg
 * constructor and a key the server leaves out keeps its default.
 */
data class AcademicSessionDto(
    val id: Long = 0,
    /** e.g. "2026-27". */
    val session: String = "",
    @SerializedName("starts_on") val startsOn: String? = null,
    @SerializedName("ends_on") val endsOn: String? = null,
    @SerializedName("term1_start") val term1Start: String? = null,
    @SerializedName("term1_end") val term1End: String? = null,
    @SerializedName("term2_start") val term2Start: String? = null,
    @SerializedName("term2_end") val term2End: String? = null,
    @SerializedName("is_current") val isCurrent: Boolean = false,
    @SerializedName("updated_at") val updatedAt: String? = null,
    @SerializedName("updated_by") val updatedBy: String? = null,
)
