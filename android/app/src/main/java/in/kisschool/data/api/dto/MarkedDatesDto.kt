package `in`.kisschool.data.api.dto

/** Response of GET /attendance/marked-dates — for a class in a range: dates with
 *  student attendance, and (separately) holiday dates. Drives the coverage calendar. */
data class MarkedDatesDto(
    val dates: List<String> = emptyList(),
    val holidays: List<String> = emptyList(),
)
