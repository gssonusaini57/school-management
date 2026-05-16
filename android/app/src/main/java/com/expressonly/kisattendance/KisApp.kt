package com.expressonly.kisattendance

import android.app.Application
import com.expressonly.kisattendance.di.AppContainer

class KisApp : Application() {
    lateinit var container: AppContainer
        private set

    override fun onCreate() {
        super.onCreate()
        container = AppContainer(this)
    }
}
