package `in`.kisschool

import android.app.Application
import `in`.kisschool.di.AppContainer

class KisApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
