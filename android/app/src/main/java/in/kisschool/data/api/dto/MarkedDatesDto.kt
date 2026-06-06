package `in`.kisschool.data.api.dto

/** Response of GET /attendance/marked-dates — the ISO dates in a range that have an
 *  attendance record for a class. Drives the dashboard coverage calendar. */
data class MarkedDatesDto(val dates: List<String> = emptyList())
