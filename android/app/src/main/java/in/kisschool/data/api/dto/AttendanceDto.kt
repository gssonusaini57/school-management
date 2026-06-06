package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

data class AttendanceDto(
    @SerializedName("class_name") val className: String,
    val date: String,
    val records: Map<String, String> = emptyMap(),
    // Day-level holiday: when true the day has no per-student records.
    // Reused as both the PUT body and the GET response.
    @SerializedName("is_holiday") val isHoliday: Boolean = false,
)
