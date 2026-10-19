package `in`.kisschool.util

import java.time.Duration
import java.time.Instant
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZoneOffset
import java.time.format.DateTimeFormatter
import java.util.Locale

/**
 * The instant a server timestamp names, or null when it is missing or unreadable. The API
 * sends ISO date-times; one with an offset ("…Z", "…+05:30") is read as given, and one
 * without is UTC, the backend's convention for the naive datetimes it stores.
 */
fun parseServerInstant(raw: String?): Instant? {
    val s = raw?.trim()?.replace(' ', 'T')?.ifEmpty { null } ?: return null
    return try {
        OffsetDateTime.parse(s).toInstant()
    } catch (_: Exception) {
        try {
            LocalDateTime.parse(s).toInstant(ZoneOffset.UTC)
        } catch (_: Exception) {
            null
        }
    }
}

private val SHORT_DATE: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM yyyy", Locale.ENGLISH)
private val DATE_TIME: DateTimeFormatter = DateTimeFormatter.ofPattern("d MMM yyyy, h:mm a", Locale.ENGLISH)

/**
 * How long ago [then] was: "just now", "5 min ago", "2 h ago", "3 d ago", and the date
 * itself ("4 Sep 2026") from 30 days on. A time slightly in the future (a phone clock
 * running behind the server) reads as "just now".
 */
fun relativeAge(then: Instant, now: Instant = Instant.now(), zone: ZoneId = ZoneId.systemDefault()): String {
    val age = Duration.between(then, now)
    return when {
        age.toMinutes() < 1 -> "just now"
        age.toMinutes() < 60 -> "${age.toMinutes()} min ago"
        age.toHours() < 24 -> "${age.toHours()} h ago"
        age.toDays() < 30 -> "${age.toDays()} d ago"
        else -> SHORT_DATE.format(then.atZone(zone))
    }
}

/** [then] as a full local date and time, e.g. "19 Oct 2026, 4:05 PM". */
fun formatDateTime(then: Instant, zone: ZoneId = ZoneId.systemDefault()): String =
    DATE_TIME.format(then.atZone(zone))
