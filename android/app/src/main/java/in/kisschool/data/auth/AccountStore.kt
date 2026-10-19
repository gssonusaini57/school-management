package `in`.kisschool.data.auth

import android.content.SharedPreferences
import `in`.kisschool.util.parseServerInstant
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import org.json.JSONArray
import org.json.JSONObject
import java.time.Instant

/**
 * An account signed in on this phone. Its [refreshToken] is the device session the server
 * opened at sign-in (POST /auth/login with remember); it is gone once the server refused
 * it, and the account then [needsPassword] to be used again but stays listed.
 */
data class SavedAccount(
    /** What was typed to sign in: the email or phone. One entry per identifier. */
    val identifier: String = "",
    val name: String = "",
    /** "super_admin" | "admin" | "staff". */
    val role: String = "",
    /** The JWT subject: "admin", "superadmin" or the staff id. */
    val accountRef: String = "",
    val refreshToken: String? = null,
    /** When [refreshToken] stops working, as the server sent it (naive UTC ISO). */
    val refreshExpiresAt: String? = null,
    /** Epoch millis of the last sign-in or refresh; the list is ordered by it. */
    val lastUsed: Long = 0L,
) {
    /** No usable refresh token: the account must sign in with its password again. */
    val needsPassword: Boolean
        get() {
            if (refreshToken.isNullOrBlank()) return true
            val expiry = parseServerInstant(refreshExpiresAt) ?: return false
            return !expiry.isAfter(Instant.now())
        }
}

/**
 * The accounts saved on this phone and which one is active (holds the access token in
 * [TokenStore]). Kept in the same encrypted preferences as the session, as a JSON array
 * written by hand (org.json): no reflection, so a release build's obfuscation can never
 * change the keys and lose everyone's sign-ins after an update.
 *
 * Writes use commit(): a rotated refresh token that didn't reach disk before the process
 * died would make the next refresh a replay, which signs the phone out.
 */
class AccountStore(private val prefs: SharedPreferences) {

    private val _accounts = MutableStateFlow(load())
    /** Most recently used first. */
    val accounts: StateFlow<List<SavedAccount>> = _accounts.asStateFlow()

    private val _activeIdentifier = MutableStateFlow(prefs.getString(KEY_ACTIVE, null))
    val activeIdentifier: StateFlow<String?> = _activeIdentifier.asStateFlow()

    /** The account whose access token [TokenStore] holds, or null when nobody is signed in. */
    val active: SavedAccount?
        get() {
            val id = _activeIdentifier.value ?: return null
            return _accounts.value.firstOrNull { it.identifier == id }
        }

    fun find(identifier: String): SavedAccount? =
        _accounts.value.firstOrNull { it.identifier == identifier }

    /**
     * Save [account], replacing the entry with the same identifier and any other entry for
     * the same server account (a teacher who signed in by phone before and by email now),
     * so each person is listed once.
     */
    @Synchronized
    fun upsert(account: SavedAccount) {
        val sameAccount = { other: SavedAccount ->
            other.identifier == account.identifier ||
                (account.accountRef.isNotBlank() && other.accountRef == account.accountRef)
        }
        val replaced = _accounts.value.filter(sameAccount)
        save(_accounts.value.filterNot(sameAccount) + account)
        // A dropped duplicate that was active hands over to the entry that replaced it.
        if (replaced.any { it.identifier == _activeIdentifier.value }) setActive(account.identifier)
    }

    /** Rewrites the saved entry for [identifier]; false when there is none (it was removed). */
    @Synchronized
    fun update(identifier: String, transform: (SavedAccount) -> SavedAccount): Boolean {
        val current = find(identifier) ?: return false
        save(_accounts.value.map { if (it.identifier == identifier) transform(current) else it })
        return true
    }

    @Synchronized
    fun remove(identifier: String) {
        save(_accounts.value.filterNot { it.identifier == identifier })
        if (_activeIdentifier.value == identifier) setActive(null)
    }

    @Synchronized
    fun setActive(identifier: String?) {
        prefs.edit().apply {
            if (identifier.isNullOrBlank()) remove(KEY_ACTIVE) else putString(KEY_ACTIVE, identifier)
        }.commit()
        _activeIdentifier.value = identifier?.ifBlank { null }
    }

    /** The server refused this account's refresh token: keep it listed as "needs password". */
    fun dropRefreshToken(identifier: String) {
        update(identifier) { it.copy(refreshToken = null, refreshExpiresAt = null) }
    }

    /**
     * Whether the "Sign in faster next time?" popup was already shown for [account] on this
     * phone. Kept apart from the saved list on purpose: logging out removes the account from
     * the list, and signing in again must not ask again (once per account, not per sign-in).
     */
    fun wasBiometricOffered(account: SavedAccount): Boolean {
        val offered = loadOffered()
        return offeredKeys(account).any { it in offered }
    }

    @Synchronized
    fun markBiometricOffered(account: SavedAccount) {
        val offered = loadOffered() + offeredKeys(account)
        prefs.edit().putString(KEY_BIOMETRIC_OFFERED, JSONArray(offered.toList()).toString()).commit()
    }

    /** The server account when known (one person, whichever identifier they typed), and the identifier. */
    private fun offeredKeys(account: SavedAccount): Set<String> = buildSet {
        if (account.accountRef.isNotBlank()) add("ref:${account.accountRef}")
        if (account.identifier.isNotBlank()) add("id:${account.identifier.trim().lowercase()}")
    }

    private fun loadOffered(): Set<String> {
        val raw = prefs.getString(KEY_BIOMETRIC_OFFERED, null) ?: return emptySet()
        return try {
            val arr = JSONArray(raw)
            (0 until arr.length()).mapNotNull { i -> arr.optString(i).ifBlank { null } }.toSet()
        } catch (_: Exception) {
            emptySet()
        }
    }

    private fun save(list: List<SavedAccount>) {
        val sorted = list.sortedByDescending { it.lastUsed }
        prefs.edit().putString(KEY_ACCOUNTS, toJson(sorted)).commit()
        _accounts.value = sorted
    }

    private fun load(): List<SavedAccount> {
        val raw = prefs.getString(KEY_ACCOUNTS, null) ?: return emptyList()
        return try {
            val arr = JSONArray(raw)
            (0 until arr.length())
                .mapNotNull { i -> arr.optJSONObject(i)?.let(::fromJson) }
                .filter { it.identifier.isNotBlank() }
                .sortedByDescending { it.lastUsed }
        } catch (_: Exception) {
            emptyList()
        }
    }

    private fun toJson(list: List<SavedAccount>): String {
        val arr = JSONArray()
        list.forEach { a ->
            arr.put(
                JSONObject()
                    .put(J_IDENTIFIER, a.identifier)
                    .put(J_NAME, a.name)
                    .put(J_ROLE, a.role)
                    .put(J_ACCOUNT_REF, a.accountRef)
                    .put(J_REFRESH_TOKEN, a.refreshToken ?: JSONObject.NULL)
                    .put(J_REFRESH_EXPIRES_AT, a.refreshExpiresAt ?: JSONObject.NULL)
                    .put(J_LAST_USED, a.lastUsed)
            )
        }
        return arr.toString()
    }

    private fun fromJson(o: JSONObject) = SavedAccount(
        identifier = o.optString(J_IDENTIFIER),
        name = o.optString(J_NAME),
        role = o.optString(J_ROLE),
        accountRef = o.optString(J_ACCOUNT_REF),
        refreshToken = o.optString(J_REFRESH_TOKEN).ifBlank { null }?.takeIf { !o.isNull(J_REFRESH_TOKEN) },
        refreshExpiresAt = o.optString(J_REFRESH_EXPIRES_AT).ifBlank { null }?.takeIf { !o.isNull(J_REFRESH_EXPIRES_AT) },
        lastUsed = o.optLong(J_LAST_USED, 0L),
    )

    private companion object {
        const val KEY_ACCOUNTS = "saved_accounts"
        const val KEY_ACTIVE = "active_account"
        const val KEY_BIOMETRIC_OFFERED = "biometric_offered"
        const val J_IDENTIFIER = "identifier"
        const val J_NAME = "name"
        const val J_ROLE = "role"
        const val J_ACCOUNT_REF = "account_ref"
        const val J_REFRESH_TOKEN = "refresh_token"
        const val J_REFRESH_EXPIRES_AT = "refresh_expires_at"
        const val J_LAST_USED = "last_used"
    }
}
