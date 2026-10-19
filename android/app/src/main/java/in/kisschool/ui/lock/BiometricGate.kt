package `in`.kisschool.ui.lock

import androidx.biometric.BiometricManager
import androidx.biometric.BiometricManager.Authenticators.BIOMETRIC_WEAK
import androidx.biometric.BiometricManager.Authenticators.DEVICE_CREDENTIAL
import androidx.biometric.BiometricPrompt
import androidx.core.content.ContextCompat
import androidx.fragment.app.FragmentActivity
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.lifecycleScope
import androidx.lifecycle.withResumed
import kotlinx.coroutines.launch

/**
 * The phone's own unlock — fingerprint, face or the screen-lock PIN / pattern — as one
 * prompt. Needs a [FragmentActivity] (androidx.biometric hosts the prompt in a fragment).
 * No CryptoObject: the prompt gates the UI; the refresh token's safety is the encrypted
 * preferences, not a key bound to the fingerprint.
 */
class BiometricGate(private val activity: FragmentActivity) {

    sealed interface Result {
        data object Success : Result

        /** Dismissed, cancelled or temporarily locked out: the person may try again. */
        data class Dismissed(val message: String?) : Result

        /**
         * Nothing enrolled, hardware missing or busy, or locked out for good: there is no
         * point retrying, so the caller falls back to the password.
         */
        data class Unavailable(val message: String?) : Result
    }

    /** Whether the phone can show the prompt at all (a fingerprint, face or screen lock is set up). */
    fun canUse(): Boolean =
        BiometricManager.from(activity).canAuthenticate(AUTHENTICATORS) == BiometricManager.BIOMETRIC_SUCCESS

    /**
     * Show the prompt, titled "Unlock KIS School Portal" with [subtitle] (the account's
     * name). The prompt can only be shown while the activity is resumed, so a call made
     * earlier (the first frame of a cold start) waits for that. [onResult] runs on the
     * main thread, once.
     */
    fun authenticate(subtitle: String, onResult: (Result) -> Unit) {
        if (!canUse()) {
            onResult(Result.Unavailable("Fingerprint, face or screen lock isn't set up on this phone."))
            return
        }
        if (activity.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)) {
            show(subtitle, onResult)
        } else {
            activity.lifecycleScope.launch {
                activity.lifecycle.withResumed { show(subtitle, onResult) }
            }
        }
    }

    private fun show(subtitle: String, onResult: (Result) -> Unit) {
        var answered = false
        fun deliver(result: Result) {
            if (answered) return
            answered = true
            onResult(result)
        }
        val callback = object : BiometricPrompt.AuthenticationCallback() {
            override fun onAuthenticationSucceeded(result: BiometricPrompt.AuthenticationResult) {
                deliver(Result.Success)
            }

            override fun onAuthenticationError(errorCode: Int, errString: CharSequence) {
                val message = errString.toString().ifBlank { null }
                deliver(
                    when (errorCode) {
                        BiometricPrompt.ERROR_NO_BIOMETRICS,
                        BiometricPrompt.ERROR_NO_DEVICE_CREDENTIAL,
                        BiometricPrompt.ERROR_HW_UNAVAILABLE,
                        BiometricPrompt.ERROR_HW_NOT_PRESENT,
                        BiometricPrompt.ERROR_LOCKOUT_PERMANENT,
                        BiometricPrompt.ERROR_SECURITY_UPDATE_REQUIRED -> Result.Unavailable(message)
                        // Cancelled by the person or the system: nothing to say.
                        BiometricPrompt.ERROR_USER_CANCELED,
                        BiometricPrompt.ERROR_NEGATIVE_BUTTON,
                        BiometricPrompt.ERROR_CANCELED -> Result.Dismissed(null)
                        // Timeout, a 30-second lockout, a vendor error: worth telling.
                        else -> Result.Dismissed(message)
                    }
                )
            }

            // One unrecognised fingerprint: the prompt stays up for another try.
            override fun onAuthenticationFailed() = Unit
        }
        val prompt = BiometricPrompt(activity, ContextCompat.getMainExecutor(activity), callback)
        val info = BiometricPrompt.PromptInfo.Builder()
            .setTitle(TITLE)
            .setSubtitle(subtitle.ifBlank { null })
            // With DEVICE_CREDENTIAL allowed there is no negative button: the PIN is the fallback.
            .setAllowedAuthenticators(AUTHENTICATORS)
            .setConfirmationRequired(false)
            .build()
        prompt.authenticate(info)
    }

    companion object {
        const val TITLE = "Unlock KIS School Portal"
        const val AUTHENTICATORS = BIOMETRIC_WEAK or DEVICE_CREDENTIAL
    }
}
