package `in`.kisschool.data.repo

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.BatchSummaryDto
import `in`.kisschool.data.api.dto.ClassAttendanceSummaryDto
import `in`.kisschool.data.api.dto.FeePaymentDto
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import retrofit2.Response
import java.time.LocalDate
import java.util.Objects

/**
 * Pending items in the super-admin's three approval queues. A queue that couldn't be read
 * is null, and [error] says why (the other counts still show).
 */
data class ApprovalCounts(
    val studentEdits: Int?,
    val marksEdits: Int?,
    val deletions: Int?,
    val error: String? = null,
) {
    val total: Int get() = (studentEdits ?: 0) + (marksEdits ?: 0) + (deletions ?: 0)
}

/**
 * [block]'s value, or the exception it failed with; coroutine cancellation still
 * propagates. For reads where one part failing must not lose the others.
 */
suspend fun <T> attemptCall(block: suspend () -> T): Result<T> = try {
    Result.success(block())
} catch (e: CancellationException) {
    throw e
} catch (e: Exception) {
    Result.failure(e)
}

/**
 * The Home dashboard's reads. Every call throws [FeatureUnavailableException] when the
 * server is older than its endpoint (404/405), so that card can hide itself with a note
 * while the others load, and [ApiException] with a message fit for the screen otherwise.
 */
class DashboardRepository(private val api: ApiService) {

    /** Attendance per class over [from]..[to] (both inclusive; the server stops at its today). */
    suspend fun classSummary(from: LocalDate, to: LocalDate): ClassAttendanceSummaryDto {
        val resp = api.attendanceClassSummary(from.toString(), to.toString())
        val body = success(resp, "the class attendance summary", "Couldn't load attendance") ?: noBody()
        if (absent(body.from) || absent(body.to) || absent(body.classes) || absent(body.totals) ||
            body.classes.any { absent(it) || absent(it.className) }
        ) throw ApiException(UNREADABLE_REPLY)
        return body
    }

    /**
     * Marks progress for [session]: every exam component of every class subject the
     * caller may see ([className] narrows to one class).
     */
    suspend fun marksSummary(session: String, className: String? = null): BatchSummaryDto {
        val resp = api.marksBatchesSummary(session, className)
        val body = success(resp, "marks progress", "Couldn't load marks progress") ?: noBody()
        if (absent(body.items) || absent(body.totals) ||
            body.items.any { absent(it) || absent(it.className) || absent(it.subject) || absent(it.examType) || absent(it.status) }
        ) throw ApiException(UNREADABLE_REPLY)
        return body
    }

    /** Every fee receipt (admins only), as the server orders them: newest first. */
    suspend fun fees(): List<FeePaymentDto> {
        val resp = api.fees()
        val body = success(resp, "the fee list", "Couldn't load fees") ?: noBody()
        if (absent(body)) throw ApiException(UNREADABLE_REPLY)
        // A receipt is never dropped (the month's total would come out short): a missing
        // text field just reads as blank.
        return body.filterNotNull().map {
            it.copy(
                studentName = text(it.studentName), className = text(it.className),
                month = text(it.month), year = text(it.year), amount = text(it.amount),
                date = text(it.date), receiptNo = text(it.receiptNo),
            )
        }
    }

    /** Staff who aren't archived (admins only). */
    suspend fun staffCount(): Int {
        val resp = api.staff()
        val body = success(resp, "the staff list", "Couldn't load staff") ?: noBody()
        if (absent(body)) throw ApiException(UNREADABLE_REPLY)
        return body.filterNotNull().count { it.status != "deleted" }
    }

    /** Students the caller may see, archived ones left out. */
    suspend fun studentTotal(): Int {
        val resp = api.studentsPage(pageSize = 1)
        val body = success(resp, "the student list", "Couldn't load students") ?: noBody()
        return body.total
    }

    /**
     * The super-admin's pending approvals, counted here: the queues list decided requests
     * too. The three are read at once; one failing still gives the other two counts.
     */
    suspend fun approvalCounts(): ApprovalCounts = coroutineScope {
        val student = async { attemptCall { api.editRequests().items.count { it.status == "pending" } } }
        val marks = async { attemptCall { api.marksEditRequests().items.count { it.status == "pending" } } }
        val deletions = async {
            attemptCall { api.deletionRequests("pending_delete").items.count { it.status == "pending_delete" } }
        }
        val results = listOf(student.await(), marks.await(), deletions.await())
        val failures = results.mapNotNull { it.exceptionOrNull() }
        if (failures.size == results.size) throw failures.first()
        ApprovalCounts(
            studentEdits = results[0].getOrNull(),
            marksEdits = results[1].getOrNull(),
            deletions = results[2].getOrNull(),
            error = failures.firstOrNull()?.userMessage("Couldn't load every approval queue"),
        )
    }

    /**
     * The body of a successful [resp], else the right exception: 404/405 mean the server
     * is older than [what]; a 403 that names a missing menu grant keeps its wording.
     */
    private fun <T> success(resp: Response<T>, what: String, fallback: String): T? {
        if (resp.isSuccessful) return resp.body()
        val code = resp.code()
        val detail = resp.apiError().message
        throw when (code) {
            404, 405 -> FeatureUnavailableException("This server doesn't offer $what yet.")
            403 -> ApiException(detail.menuGrantDenial() ?: detail ?: "You don't have access to $what.", code)
            else -> ApiException(detail ?: "$fallback (HTTP $code)", code)
        }
    }

    private fun noBody(): Nothing = throw ApiException("The server sent an empty reply.")

    /** A null check the compiler can't drop for a non-null type (it is a plain call). */
    private fun absent(value: Any?): Boolean = Objects.isNull(value)

    /** [value], or "" for the explicit JSON null Gson can put in a non-null field. */
    private fun text(value: String?): String = if (absent(value)) "" else value.toString()

    private companion object {
        const val UNREADABLE_REPLY = "The server sent a reply this app can't read. Please update the app."
    }
}
