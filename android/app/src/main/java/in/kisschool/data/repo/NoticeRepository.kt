package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.NoticeDto
import `in`.kisschool.util.parseServerInstant
import java.time.Instant

/** How urgent a notice is, from the server's "normal" | "medium" | "high". */
enum class NoticePriority {
    HIGH, MEDIUM, NORMAL;

    companion object {
        /** Anything the app doesn't know (or a missing value) reads as [NORMAL]. */
        fun from(raw: String?): NoticePriority = when (raw?.trim()?.lowercase()) {
            "high" -> HIGH
            "medium" -> MEDIUM
            else -> NORMAL
        }
    }
}

/** A notice ready to show: no nulls, the priority parsed and the time read. */
data class Notice(
    val id: Long,
    val title: String,
    val content: String,
    val priority: NoticePriority,
    val audience: String,
    val postedBy: String,
    /** When it was posted; null if the server's timestamp couldn't be read. */
    val createdAt: Instant?,
)

/** Notices are readable by every signed-in user; only admins post or delete them (on the web). */
class NoticeRepository(private val api: ApiService) {

    /** Every notice, newest first (a notice without a readable time goes last). */
    suspend fun list(): List<Notice> =
        api.notices()
            .filterNotNull()
            .map { it.toNotice() }
            .sortedWith(compareByDescending<Notice, Instant?>(nullsFirst()) { it.createdAt }.thenByDescending { it.id })
}

private fun NoticeDto.toNotice() = Notice(
    id = id,
    title = title?.trim().orEmpty(),
    content = content?.trim().orEmpty(),
    priority = NoticePriority.from(priority),
    audience = audience?.trim().orEmpty(),
    postedBy = postedBy?.trim().orEmpty(),
    createdAt = parseServerInstant(createdAt),
)
