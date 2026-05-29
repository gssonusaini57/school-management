package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.AttendanceDto

class AttendanceRepository(private val api: ApiService) {

    /** Returns the saved attendance for (class, date) or null if no record exists yet. */
    suspend fun fetch(className: String, date: String): AttendanceDto? {
        val resp = api.attendance(className, date)
        if (resp.code() == 404) return null
        if (!resp.isSuccessful) error("HTTP ${resp.code()}")
        return resp.body()
    }

    suspend fun save(className: String, date: String, records: Map<Long, String>) {
        val body = AttendanceDto(
            className = className,
            date = date,
            records = records.mapKeys { it.key.toString() }
        )
        val resp = api.saveAttendance(body)
        if (!resp.isSuccessful) error("HTTP ${resp.code()}")
    }
}
