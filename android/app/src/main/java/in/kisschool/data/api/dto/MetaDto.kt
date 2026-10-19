package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * GET /meta — reference lists served from the backend's single copies
 * (backend/app/routers/meta.py). All parameters are defaulted so Gson uses the
 * no-arg constructor and a key the server leaves out keeps its default; the app
 * keeps its own fallbacks for servers that don't have /meta at all.
 */
data class MetaDto(
    val classes: List<String> = emptyList(),
    @SerializedName("grade_bands") val gradeBands: List<GradeBandDto> = emptyList(),
    @SerializedName("grade_legend") val gradeLegend: List<GradeLegendDto> = emptyList(),
    /** Letters a teacher picks for a graded exam, best first (A1 … D). */
    @SerializedName("grade_letters") val gradeLetters: List<String> = emptyList(),
    val houses: List<String> = emptyList(),
    @SerializedName("promotion_values") val promotionValues: List<String> = emptyList(),
    @SerializedName("pass_pct") val passPct: Double = 33.0,
    @SerializedName("conditional_max_fails") val conditionalMaxFails: Int = 2,
    val scopes: List<String> = emptyList(),
    @SerializedName("menu_keys") val menuKeys: List<String> = emptyList(),
)

/** A grade and the minimum percentage that earns it. */
data class GradeBandDto(
    val grade: String = "",
    @SerializedName("min_pct") val minPct: Double = 0.0,
)

/** A grade and its printable range, e.g. "91–100". */
data class GradeLegendDto(
    val grade: String = "",
    val range: String = "",
)
