package `in`.kisschool.data.auth

import okhttp3.Authenticator
import okhttp3.Request
import okhttp3.Response
import okhttp3.Route

/**
 * Answers a 401 with the same request carrying a fresh access token, after one silent
 * refresh through [SessionManager] (single-flight: concurrent 401s share one refresh).
 *
 * Gives up (the 401 reaches the caller) for the auth routes themselves, and after one
 * retry: OkHttp chains retries through [Response.priorResponse], so a second 401 on the
 * retried request is final. When the refresh is refused, [SessionManager] has already
 * cleared the active session and told the app, which returns to the login screen.
 */
class TokenAuthenticator(private val sessions: SessionManager) : Authenticator {

    override fun authenticate(route: Route?, response: Response): Request? {
        val request = response.request
        if (isAuthRoute(request)) return null
        if (response.priorResponse != null) return null
        val sent = request.header("Authorization")
            ?.removePrefix("Bearer")
            ?.trim()
            ?.ifBlank { null }
        val token = sessions.tokenForRetry(sent) ?: return null
        return request.newBuilder().header("Authorization", "Bearer $token").build()
    }

    private fun isAuthRoute(request: Request): Boolean {
        val path = request.url.encodedPath
        return BYPASS.any { path.endsWith(it) }
    }

    private companion object {
        /** A 401 from these is an answer, never an expired access token. */
        val BYPASS = listOf("/auth/login", "/auth/refresh", "/auth/logout")
    }
}
