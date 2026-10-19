package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * A class report-card template (backend/app/routers/pdf_templates.py, TemplateOut),
 * as returned by GET /pdf/templates/resolve. The template's free-form `data` JSON
 * is admin configuration the app never reads, so it is not mapped (Gson skips
 * unknown keys). All parameters are defaulted so Gson uses the no-arg constructor.
 */
data class PdfTemplateDto(
    val id: Long = 0,
    val kind: String = "",
    @SerializedName("class_name") val className: String = "",
    val session: String = "",
    /** Display label printed on the card, e.g. "Term I". */
    val term: String? = null,
    /** term1 | term2 | annual. */
    val scope: String? = null,
    /** summary | components. */
    val layout: String = "summary",
    val version: Int = 0,
    @SerializedName("updated_at") val updatedAt: String? = null,
)

/**
 * POST /pdf/templates/{id}/render body. `include_drafts` is deliberately absent:
 * only a super-admin may send it (anyone else gets a 403), and leaving it out
 * keeps the template's own setting.
 */
data class RenderRequestBody(
    @SerializedName("student_ids") val studentIds: List<Long>,
    val force: Boolean = false,
)

/** One student's outcome from a render call. */
data class RenderResultDto(
    @SerializedName("student_id") val studentId: Long = 0,
    /** cached | rendered | error. */
    val status: String = "",
    /** Id for GET /pdf/cache/{id}; null when the render failed. */
    @SerializedName("pdf_id") val pdfId: Long? = null,
    val error: String? = null,
    /** e.g. draft marks left out, date of birth missing. */
    val warnings: List<String> = emptyList(),
)

data class RenderResponseDto(
    val results: List<RenderResultDto> = emptyList(),
)
