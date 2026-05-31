package `in`.kisschool.data.repo

import `in`.kisschool.BuildConfig
import `in`.kisschool.data.api.ApiService
import `in`.kisschool.data.api.dto.AppVersionDto

/**
 * Fetches the published version manifest (downloads/app-version.json) so the UI
 * can force-update stale installs. Network/parse failures return null — the gate
 * MUST fail open so a server hiccup never bricks the app for working teachers.
 */
class AppUpdateRepository(private val api: ApiService) {

    val installedVersionCode: Int get() = BuildConfig.VERSION_CODE

    suspend fun fetch(): AppVersionDto? = try {
        api.appVersion(BuildConfig.APP_VERSION_URL)
    } catch (_: Exception) {
        null
    }
}
