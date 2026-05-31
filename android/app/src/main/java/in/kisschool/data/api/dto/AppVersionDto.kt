package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/**
 * Version manifest published next to the APK (downloads/app-version.json), written
 * by scripts/build-android.sh on every release. The app fetches it on launch:
 *  - installed versionCode < [minVersionCode]    → forced update (app is blocked)
 *  - installed versionCode < [latestVersionCode] → optional update prompt
 *
 * Defaults are deliberately permissive (0) so a missing/garbled manifest never
 * locks anyone out — the gate fails open.
 */
data class AppVersionDto(
    @SerializedName("latest_version_code") val latestVersionCode: Int = 0,
    @SerializedName("min_version_code") val minVersionCode: Int = 0,
    @SerializedName("latest_version_name") val latestVersionName: String? = null,
    @SerializedName("apk_url") val apkUrl: String? = null,
    val notes: String? = null,
)
