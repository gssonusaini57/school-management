package `in`.kisschool.data.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

/**
 * The one encrypted preferences file secrets live in: the active session ([TokenStore])
 * and the accounts saved on this phone with their refresh tokens ([AccountStore]). One
 * file, opened once, so both stores share the master key and the backup exclusion in
 * res/xml/data_extraction_rules.xml covers everything secret.
 */
object SecurePrefs {
    const val FILE_NAME = "kis_secure_prefs"

    fun open(context: Context): SharedPreferences {
        val masterKey = MasterKey.Builder(context.applicationContext)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        return EncryptedSharedPreferences.create(
            context.applicationContext,
            FILE_NAME,
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM
        )
    }
}
