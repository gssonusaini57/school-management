package `in`.kisschool.data.repo

import com.google.gson.JsonParseException
import org.json.JSONArray
import org.json.JSONObject
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.net.UnknownHostException
import java.util.concurrent.CancellationException

/** A failed API call, already phrased for the person using the app. */
open class ApiException(message: String, val code: Int = 0) : RuntimeException(message)

/** The server is older than the feature (its endpoint answers 404/405/422). */
class FeatureUnavailableException(message: String) : ApiException(message)

/**
 * The FastAPI error body of a failed response.
 *
 * `detail` comes in three shapes: a plain string (most errors), an object
 * `{message, rows}` (the marks range check) or a list `[{loc, msg, type}]`
 * (request validation, e.g. an older server that doesn't know a field).
 * [validation] is true for the list shape.
 */
internal data class ApiErrorBody(val message: String?, val validation: Boolean)

internal fun Response<*>.apiError(): ApiErrorBody {
    val raw = try {
        errorBody()?.string()
    } catch (_: Exception) {
        null
    } ?: return ApiErrorBody(null, false)
    return try {
        when (val d = JSONObject(raw).opt("detail")) {
            is String -> ApiErrorBody(d.ifBlank { null }, false)
            is JSONObject -> ApiErrorBody(d.optString("message").ifBlank { null } ?: d.toString(), false)
            is JSONArray -> {
                val first = (0 until d.length())
                    .mapNotNull { i -> (d.opt(i) as? JSONObject)?.optString("msg")?.ifBlank { null } }
                    .firstOrNull()
                ApiErrorBody(first, true)
            }
            null, JSONObject.NULL -> ApiErrorBody(null, false)
            else -> ApiErrorBody(d.toString(), false)
        }
    } catch (_: Exception) {
        ApiErrorBody(null, false)
    }
}

/**
 * This detail when it is the 403 for a staff menu grant that is switched off
 * (deps.assert_menu: "Your account doesn't have access to results. Ask an admin to
 * enable it."), else null. It already says what to do, so screens show it as is.
 */
internal fun String?.menuGrantDenial(): String? =
    this?.takeIf { it.startsWith("Your account doesn't have access") }

private const val UNREADABLE = "The server sent a reply this app can't read. Please update the app."

/**
 * A readable message for any failure from a repository call. Callers rethrow
 * coroutine cancellation before getting here; it is mapped only defensively.
 */
fun Throwable.userMessage(fallback: String): String = when (this) {
    is CancellationException -> fallback
    is ApiException -> message?.takeIf { it.isNotBlank() } ?: fallback
    is SocketTimeoutException -> "The server took too long to answer. Please try again."
    is UnknownHostException, is ConnectException -> "Can't reach the server. Check your internet connection."
    is IOException -> "Network error. Please check your connection."
    is HttpException -> "$fallback (HTTP ${code()})"
    is JsonParseException -> UNREADABLE
    // Retrofit's Gson converter lets the reader's "Expected BEGIN_OBJECT but was …" through raw.
    is IllegalStateException -> if (message?.startsWith("Expected ") == true) UNREADABLE else message ?: fallback
    else -> message?.takeIf { it.isNotBlank() } ?: fallback
}
