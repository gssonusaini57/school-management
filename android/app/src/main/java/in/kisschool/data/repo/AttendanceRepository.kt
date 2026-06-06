package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.AttendanceDto

/** Coverage for a class+month: dates with student attendance, and holiday dates. */
data class Coverage(val marked: Set<String>, val holidays: Set<String>)

class AttendanceRepository(private val api: ApiService) {

    /** Returns the saved attendance for (class, date) or null if no record exists yet. */
    suspend fun fetch(className: String, date: String): AttendanceDto? {
        val resp = api.attendance(className, date)
        if (resp.code() == 404) return null
        if (!resp.isSuccessful) error("HTTP ${resp.code()}")
        return resp.body()
    }

    suspend fun save(className: String, date: String, records: Map<Long, String>, isHoliday: Boolean = false) {
        val body = AttendanceDto(
            className = className,
            date = date,
            records = if (isHoliday) emptyMap() else records.mapKeys { it.key.toString() },
            isHoliday = isHoliday,
        )
        val resp = api.saveAttendance(body)
        if (!resp.isSuccessful) error("HTTP ${resp.code()}")
    }

    /** Clear a wrongly-marked day entirely (also clears a holiday). */
    suspend fun clear(className: String, date: String) {
        val resp = api.clearAttendance(className, date)
        if (!resp.isSuccessful) error("HTTP ${resp.code()}")
    }

    /** Marked + holiday ISO dates in [from,to]. Sets for O(1) per-day lookups. */
    suspend fun markedDates(className: String, from: String, to: String): Coverage {
        val r = api.markedDates(className, from, to)
        return Coverage(marked = r.dates.toSet(), holidays = r.holidays.toSet())
    }
}
