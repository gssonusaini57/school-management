package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.AcademicSessionDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import java.time.LocalDate

/** What a session picker offers, and which entry it starts on. */
data class SessionChoice(
    /** Session names, newest first; always contains [current]. */
    val names: List<String>,
    /**
     * The server's current session (the one flagged current, else the one whose dates
     * contain today); without one, the April-rollover name for today.
     */
    val current: String,
    /** [current]'s row (term dates), when the server has one. */
    val currentRow: AcademicSessionDto?,
    /** True when the server listed its sessions (false offline or on an older server). */
    val fromServer: Boolean,
)

/**
 * Academic sessions (school years) from GET /sessions and GET /sessions/current.
 *
 * Marks, results and report cards are all keyed by a session name such as
 * "2026-27". The server owns the list; when it can't be reached, is older than the
 * sessions feature, or has no session for today, [choice] falls back to the name of
 * the school year that contains today (April rollover), so Jan–Mar 2027 is still "2026-27".
 */
class SessionRepository(private val api: ApiService) {

    @Volatile private var cached: Pair<Long, SessionChoice>? = null

    /** Every configured session, newest first. Throws [ApiException] / IOException on failure. */
    suspend fun sessions(): List<AcademicSessionDto> {
        val resp = api.sessions()
        if (resp.isSuccessful) return resp.body().orEmpty().filter { it.session.isNotBlank() }
        if (resp.code() == 404) throw FeatureUnavailableException("This server doesn't list academic sessions yet.")
        throw ApiException(resp.apiError().message ?: "Couldn't load sessions (HTTP ${resp.code()})", resp.code())
    }

    /** The server's current session, or null when none is configured. Throws on network failure. */
    suspend fun current(): AcademicSessionDto? {
        val resp = api.currentSession()
        if (resp.isSuccessful) return resp.body()?.takeIf { it.session.isNotBlank() }
        if (resp.code() == 404) return null      // none configured, or an older server
        throw ApiException(resp.apiError().message ?: "Couldn't load the current session (HTTP ${resp.code()})", resp.code())
    }

    /**
     * Picker contents plus the default session. Never throws (except coroutine
     * cancellation): any failure falls back to [fallbackSessionName]. A server
     * answer is reused for a few minutes so opening screens stays quick.
     */
    suspend fun choice(today: LocalDate = LocalDate.now()): SessionChoice {
        cached?.let { (at, c) -> if (System.currentTimeMillis() - at < CACHE_MS) return c }
        val (list, currentRow) = coroutineScope {
            val listCall = async { orNull { sessions() } }
            val currentCall = async { orNull { current() } }
            listCall.await() to currentCall.await()
        }
        // GET /sessions/current answers "flagged current, else the row containing
        // today"; repeat that on the list in case only the list call got through.
        // With neither (e.g. April, before the new session is added) today's
        // April-rollover name stands in and joins the names below, never the newest
        // listed session: that would quietly file new marks under last year, while a
        // name the server doesn't have is refused on save (422) with what to pick.
        val match = currentRow
            ?: list?.firstOrNull { it.isCurrent }
            ?: list?.firstOrNull { it.covers(today) }
        val current = match?.session ?: fallbackSessionName(today)
        // The stand-in's own row (term dates) in case the server lists it after all.
        val row = match ?: list?.firstOrNull { it.session == current }
        val names = (list.orEmpty().map { it.session } + current).distinct().sortedDescending()
        val choice = SessionChoice(names = names, current = current, currentRow = row, fromServer = list != null)
        if (list != null) cached = System.currentTimeMillis() to choice
        return choice
    }

    private suspend fun <T> orNull(block: suspend () -> T): T? = try {
        block()
    } catch (e: CancellationException) {
        throw e
    } catch (_: Exception) {
        null
    }

    companion object {
        private const val CACHE_MS = 5 * 60_000L

        /** The school year containing [today], April to March: Feb 2027 → "2026-27", Apr 2027 → "2027-28". */
        fun fallbackSessionName(today: LocalDate = LocalDate.now()): String {
            val y = if (today.monthValue >= 4) today.year else today.year - 1
            // Plain templates, not String.format: a device locale must not change the digits.
            return "$y-${((y + 1) % 100).toString().padStart(2, '0')}"
        }

        /**
         * The term [today] falls in for [row], as a results scope: "term2" from Term 2's
         * start date, else "term1". Without a row, Oct–Mar counts as Term 2.
         */
        fun termScopeFor(row: AcademicSessionDto?, today: LocalDate = LocalDate.now()): String {
            val t2 = row?.term2Start?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
            val inTerm2 = if (t2 != null) !today.isBefore(t2) else today.monthValue >= 10 || today.monthValue <= 3
            return if (inTerm2) "term2" else "term1"
        }
    }
}

/** True when [day] lies within the session's start/end dates (ISO strings compare in date order). */
private fun AcademicSessionDto.covers(day: LocalDate): Boolean {
    val start = startsOn ?: return false
    val end = endsOn ?: return false
    val d = day.toString()
    return start <= d && d <= end
}
