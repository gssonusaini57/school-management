package `in`.kisschool

import android.app.Application
import coil.ImageLoader
import coil.ImageLoaderFactory
import `in`.kisschool.di.AppContainer

class KisApp : Application(), ImageLoaderFactory {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }

    /**
     * Coil's default loader, used by every AsyncImage: the app's own HTTP client, so
     * student document images carry the Bearer header (and a 401 refreshes the session
     * like any other request) instead of a `?token=` in the URL.
     */
    override fun newImageLoader(): ImageLoader =
        ImageLoader.Builder(this)
            .okHttpClient { container.httpClient }
            .build()
}
