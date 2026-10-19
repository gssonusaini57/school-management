package `in`.kisschool.data.auth

import android.util.Base64
import org.json.JSONObject

/** The claims this app reads off an access token. Nothing is verified: only the server does that. */
data class JwtClaims(
    /** The account the token names: "admin", "superadmin" or a staff id. */
    val sub: String?,
    /** Expiry, seconds since the epoch. */
    val exp: Long?,
    /** The device-session row the token was minted from; null for a sign-in without one. */
    val sid: Long?,
)

object Jwt {

    /** The payload claims of [token], or null when it is blank or not a readable JWT. */
    fun claims(token: String?): JwtClaims? {
        if (token.isNullOrBlank()) return null
        val parts = token.split('.')
        if (parts.size < 2) return null
        return try {
            val json = String(
                Base64.decode(parts[1], Base64.URL_SAFE or Base64.NO_PADDING or Base64.NO_WRAP),
                Charsets.UTF_8,
            )
            val o = JSONObject(json)
            JwtClaims(
                sub = o.optString("sub").ifBlank { null },
                exp = if (o.has("exp") && !o.isNull("exp")) o.optLong("exp") else null,
                sid = if (o.has("sid") && !o.isNull("sid")) o.optLong("sid") else null,
            )
        } catch (_: Exception) {
            null
        }
    }

    /**
     * True when [token] is missing, unreadable, or expires within [skewSeconds] (a token
     * about to expire is treated as expired, so a request sent with it isn't refused
     * on arrival).
     */
    fun isExpired(token: String?, skewSeconds: Long = 60): Boolean {
        val exp = claims(token)?.exp ?: return true
        return exp - skewSeconds <= System.currentTimeMillis() / 1000
    }
}
