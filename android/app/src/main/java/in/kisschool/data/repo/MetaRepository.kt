package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.MetaDto
import kotlinx.coroutines.CancellationException

/**
 * GET /meta reference lists (grade letters, houses, …), fetched once per app run.
 * Never throws: offline or on a server without /meta the callers get the static
 * fallbacks below, which match what the backend serves today.
 */
class MetaRepository(private val api: ApiService) {

    @Volatile private var cached: MetaDto? = null

    /** The server's reference lists, or null when they can't be loaded right now. */
    suspend fun meta(): MetaDto? {
        cached?.let { return it }
        return try {
            val resp = api.meta()
            if (resp.isSuccessful) resp.body()?.also { cached = it } else null
        } catch (e: CancellationException) {
            throw e
        } catch (_: Exception) {
            null
        }
    }

    /** Letters for a graded exam, best first. */
    suspend fun gradeLetters(): List<String> =
        meta()?.gradeLetters?.map { it.trim() }?.filter { it.isNotEmpty() }?.takeIf { it.isNotEmpty() }
            ?: FALLBACK_GRADE_LETTERS

    companion object {
        /** Mirrors GRADE_LETTERS in backend/app/services/results.py. */
        val FALLBACK_GRADE_LETTERS: List<String> = listOf("A1", "A2", "B1", "B2", "C1", "C2", "D")
    }
}
