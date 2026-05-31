package `in`.kisschool

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.ui.Modifier
import androidx.navigation.compose.rememberNavController
import `in`.kisschool.ui.nav.AppNav
import `in`.kisschool.ui.nav.Routes
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.update.UpdateGate

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        val container = (application as KisApp).container

        setContent {
            KISTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    // Force-update gate wraps the whole app: a too-old build is
                    // blocked by a non-dismissable overlay until it's updated.
                    UpdateGate(repo = container.appUpdateRepo) {
                        val nav = rememberNavController()
                        val startRoute = when {
                            !container.authRepo.isLoggedIn -> Routes.LOGIN
                            container.authRepo.forcePasswordChange -> Routes.CHANGE_PASSWORD
                            else -> Routes.HOME
                        }
                        AppNav(navController = nav, startRoute = startRoute, container = container)

                        LaunchedEffect(Unit) {
                            container.authExpired.collect {
                                nav.navigate(Routes.LOGIN) {
                                    popUpTo(0) { inclusive = true }
                                    launchSingleTop = true
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
