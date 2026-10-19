package `in`.kisschool.data.auth

import java.util.concurrent.atomic.AtomicReference

/**
 * A one-shot message for the next login screen: the identifier to prefill and a notice
 * to show ("your sign-in has expired"). Posted by whoever sends the app back to Login
 * (the lock gate, the authenticator after a refused refresh) and taken once by the login
 * ViewModel when it is created.
 */
class LoginHandoff {

    data class Data(val identifier: String?, val notice: String?)

    private val pending = AtomicReference<Data?>(null)

    fun post(identifier: String?, notice: String?) {
        pending.set(Data(identifier?.ifBlank { null }, notice?.ifBlank { null }))
    }

    fun take(): Data? = pending.getAndSet(null)

    companion object {
        const val EXPIRED_NOTICE = "Your sign-in on this phone has expired. Enter your password."
    }
}
