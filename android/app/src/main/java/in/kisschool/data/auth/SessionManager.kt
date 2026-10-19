package `in`.kisschool.data.auth

import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.LoginResponse
import `in`.kisschool.data.api.dto.RefreshRequest
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import retrofit2.HttpException
import retrofit2.Response
import java.io.IOException
import java.net.ConnectException
import java.net.UnknownHostException

/**
 * The one place a refresh token is spent, and the one place the active session changes.
 * Every path that needs a fresh access token (the OkHttp [TokenAuthenticator] on a 401, the
 * app-lock gate, a saved account tapped on the login screen) comes through [lock], so two
 * requests failing at the same moment cause one refresh, not two (the second would be a
 * replay and sign the phone out).
 *
 * Order on success is fixed: the NEW refresh token is written first (each is single-use,
 * so losing it means a replay next time), then the access token and user metadata.
 *
 * Two locks. [lock] is held for a whole refresh, network call included, and only ever on
 * a background thread. [stateLock] guards the active session (which account is active,
 * its access token) for a few microseconds at a time, so the main thread can end or switch
 * a session without waiting for a refresh. Every local change of the active session
 * (a sign-in, Logout, Switch account, a session lost) bumps [epoch]; a refresh that
 * started before such a change still saves its new refresh token but never makes its
 * account active again, so a Logout can't be undone by a refresh finishing a moment later.
 *
 * [api] must be built on a client with no Bearer header and no authenticator.
 */
class SessionManager(
    private val api: ApiService,
    private val tokenStore: TokenStore,
    private val accounts: AccountStore,
    /** The active session is gone for good (refresh refused, or nothing to refresh with). */
    private val onSessionLost: (lost: SavedAccount?) -> Unit,
) {
    private val lock = Any()
    private val stateLock = Any()

    /** Guarded by [stateLock]. */
    private var epoch = 0L

    sealed interface RefreshResult {
        /** [token] is the access token to use now. */
        data class Refreshed(val token: String, val mustChange: Boolean) : RefreshResult
        /** The server refused the refresh token (or there was none): sign in with the password. */
        data object NeedsPassword : RefreshResult
        /** Network or server trouble: nothing changed, try again later. */
        data class Failed(val error: Throwable) : RefreshResult
        /**
         * The refresh worked (its new refresh token is saved), but the phone signed out or
         * switched account meanwhile, or the account was removed: there is nothing to use.
         */
        data object Superseded : RefreshResult
    }

    /** Save a password sign-in: the account (replacing an older entry), made active, and its session. */
    fun storeSignIn(identifier: String, resp: LoginResponse): SavedAccount = synchronized(stateLock) {
        epoch++
        val previous = accounts.find(identifier)
        val account = SavedAccount(
            identifier = identifier,
            name = resp.name,
            role = resp.role,
            accountRef = Jwt.claims(resp.token)?.sub ?: previous?.accountRef.orEmpty(),
            refreshToken = resp.refreshToken,
            refreshExpiresAt = resp.refreshExpiresAt,
            lastUsed = System.currentTimeMillis(),
        )
        accounts.upsert(account)
        accounts.setActive(identifier)
        saveSession(resp)
        account
    }

    /**
     * Save a sign-in on a server without device sessions: just the one-hour access token,
     * with no saved account active, so nothing pairs it with someone else's refresh token.
     */
    fun storeLegacySignIn(resp: LoginResponse) = synchronized(stateLock) {
        epoch++
        accounts.setActive(null)
        saveSession(resp)
    }

    /**
     * Runs [block], a local end of the active session (Logout, Switch account, removing the
     * active account), so that a refresh finishing at the same moment never brings it back.
     */
    fun <T> endActiveSession(block: () -> T): T = synchronized(stateLock) {
        epoch++
        block()
    }

    /** Spend [account]'s refresh token for a new session, making it the active account. */
    suspend fun refresh(account: SavedAccount): RefreshResult = withContext(Dispatchers.IO) {
        synchronized(lock) {
            refreshLocked(account, startEpoch = synchronized(stateLock) { epoch }, activate = true)
        }
    }

    /**
     * The app-lock gate's step after an unlock: the active account's access token if it
     * is still good, else a refresh. [RefreshResult.NeedsPassword] when nobody is active.
     */
    suspend fun resumeActive(): RefreshResult = withContext(Dispatchers.IO) {
        synchronized(lock) {
            val (active, token, startEpoch) = synchronized(stateLock) {
                Triple(accounts.active, tokenStore.token, epoch)
            }
            if (active == null) return@synchronized RefreshResult.NeedsPassword
            if (token != null && !Jwt.isExpired(token)) {
                return@synchronized RefreshResult.Refreshed(token, tokenStore.forcePasswordChange)
            }
            refreshLocked(active, startEpoch, activate = true)
        }
    }

    /**
     * For [TokenAuthenticator], on the request's own thread: the access token to retry a
     * 401 with, or null to let the 401 stand. [sentToken] is the one the failed request
     * carried; if the stored token already differs (another request refreshed while this
     * one waited for the lock) it is simply reused. A request is only ever retried as the
     * account it was sent as. A refusal ends the active session.
     */
    fun tokenForRetry(sentToken: String?): String? = synchronized(lock) {
        val (stored, active, startEpoch) = synchronized(stateLock) {
            Triple(tokenStore.token, accounts.active, epoch)
        }
        val sentAs = Jwt.claims(sentToken)?.sub
        if (!stored.isNullOrBlank() && stored != sentToken && !Jwt.isExpired(stored, skewSeconds = 0)) {
            // Refreshed while this request waited; a token of another account is not its to use.
            return@synchronized stored.takeIf { sentAs == null || Jwt.claims(it)?.sub == sentAs }
        }
        if (sentAs != null && active != null && active.accountRef.isNotBlank() && active.accountRef != sentAs) {
            // Sent as an account the phone has switched away from: nothing to refresh for it.
            return@synchronized null
        }
        if (active?.refreshToken.isNullOrBlank()) {
            // Nothing to refresh with: an older server's one-hour sign-in has ended, or the
            // session was refused already. Nothing stored at all means the phone already
            // left that session (Logout, Switch account): the 401 just stands.
            if (!stored.isNullOrBlank()) sessionLost(active, startEpoch)
            return@synchronized null
        }
        when (val r = refreshLocked(active!!, startEpoch, activate = false)) {
            is RefreshResult.Refreshed -> r.token
            RefreshResult.NeedsPassword -> {
                sessionLost(active, startEpoch)
                null
            }
            // Transient: the caller sees the 401; the next request tries again.
            is RefreshResult.Failed -> null
            RefreshResult.Superseded -> null
        }
    }

    /**
     * One refresh of [requested]'s session, under [lock]. [activate]: the person asked for
     * this account (the login screen, the lock gate), so it becomes the active one; else
     * (the authenticator) it only stays active if nothing changed since [startEpoch].
     */
    private fun refreshLocked(requested: SavedAccount, startEpoch: Long, activate: Boolean): RefreshResult {
        // Re-read under the lock: a refresh that just finished may have rotated the token.
        val account = accounts.find(requested.identifier) ?: return RefreshResult.NeedsPassword
        if (account.refreshToken != requested.refreshToken) {
            val usable = synchronized(stateLock) {
                tokenStore.token?.takeIf { accounts.activeIdentifier.value == account.identifier && !Jwt.isExpired(it) }
            }
            if (usable != null) return RefreshResult.Refreshed(usable, tokenStore.forcePasswordChange)
        }
        val refreshToken = account.refreshToken ?: return RefreshResult.NeedsPassword
        val response = try {
            execute(refreshToken)
        } catch (e: IOException) {
            return RefreshResult.Failed(e)
        } catch (e: RuntimeException) {
            return RefreshResult.Failed(e)
        }
        if (response.isSuccessful) {
            val body = response.body()
            if (body == null || body.token.isBlank()) {
                return RefreshResult.Failed(IllegalStateException("Empty refresh response"))
            }
            return if (persistRefreshed(account.identifier, body, startEpoch, activate)) {
                RefreshResult.Refreshed(body.token, body.forcePasswordChange)
            } else {
                RefreshResult.Superseded
            }
        }
        if (response.code() == 401) {
            // Revoked, expired, replayed or the account is gone: the token is dead. The
            // account stays listed, flagged "needs password"; its access token goes too,
            // if it is still the session in use.
            synchronized(stateLock) {
                accounts.dropRefreshToken(account.identifier)
                if (epoch == startEpoch && accounts.activeIdentifier.value == account.identifier) tokenStore.clear()
            }
            return RefreshResult.NeedsPassword
        }
        return RefreshResult.Failed(HttpException(response))
    }

    /**
     * POST /auth/refresh, asked once more at once when the answer was lost on the way
     * (a timeout, a dropped connection): the server may already have rotated the token,
     * and it honours the same token again within 60 s, so an immediate retry heals what a
     * later one would find a replay (which signs the phone out). A request that never left
     * the phone (no network, DNS, connection refused) is not retried.
     */
    private fun execute(refreshToken: String): Response<LoginResponse> = try {
        api.refreshCall(RefreshRequest(refreshToken)).execute()
    } catch (e: IOException) {
        if (e is UnknownHostException || e is ConnectException) throw e
        api.refreshCall(RefreshRequest(refreshToken)).execute()
    }

    /** Saves a refresh's answer; true when the account is now the active session. */
    private fun persistRefreshed(identifier: String, resp: LoginResponse, startEpoch: Long, activate: Boolean): Boolean =
        synchronized(stateLock) {
            // The new refresh token is kept whatever happened meanwhile (the old one is
            // spent), written first, with commit().
            val saved = accounts.update(identifier) {
                it.copy(
                    name = resp.name.ifBlank { it.name },
                    role = resp.role.ifBlank { it.role },
                    accountRef = Jwt.claims(resp.token)?.sub ?: it.accountRef,
                    refreshToken = resp.refreshToken ?: it.refreshToken,
                    refreshExpiresAt = resp.refreshExpiresAt ?: it.refreshExpiresAt,
                    lastUsed = System.currentTimeMillis(),
                )
            }
            // Removed meanwhile: its removal already ended the session on the server.
            if (!saved) return@synchronized false
            val stillActive = epoch == startEpoch && accounts.activeIdentifier.value == identifier
            if (!activate && !stillActive) return@synchronized false
            if (!stillActive) epoch++
            accounts.setActive(identifier)
            saveSession(resp)
            true
        }

    private fun saveSession(resp: LoginResponse) {
        tokenStore.saveSession(
            resp.token, resp.name, resp.allowedClasses, resp.forcePasswordChange, resp.role,
            allowedMenus = resp.allowedMenus,
        )
    }

    /** The session the authenticator was refreshing is over, unless the phone already moved on. */
    private fun sessionLost(active: SavedAccount?, startEpoch: Long) {
        val lost = synchronized(stateLock) {
            if (epoch != startEpoch) return@synchronized false
            epoch++
            tokenStore.clear()
            true
        }
        if (lost) onSessionLost(active)
    }
}
