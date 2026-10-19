package `in`.kisschool.ui.nav

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.compose.rememberNavController
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.di.AppContainer
import `in`.kisschool.ui.lock.BiometricGate
import `in`.kisschool.ui.lock.LockGate
import `in`.kisschool.ui.lock.LockOutcome

/**
 * The app under its lock. Behind a cold-start lock nothing of the app is composed, so no
 * request leaves (and no session is refreshed) before the unlock; the screen it then opens
 * on is chosen from the session as the unlock left it. Once shown, the app stays composed
 * and a later lock (15 minutes in the background) covers it, so the person comes back to
 * the screen they were on, unsaved marks and all.
 *
 * Every way off the lock screen to the sign-in screens ("Use password", "Switch account",
 * a refused refresh, no usable fingerprint / face / PIN) first steps out of the active
 * session on this phone (AuthRepository.leaveSession): nothing stays signed in behind a
 * login screen the person could back out of, and the saved accounts still open from the
 * login screen's list, behind the same unlock.
 */
@Composable
fun AppRoot(container: AppContainer, gate: BiometricGate, onExit: () -> Unit) {
    val appLock = container.appLock
    val auth = container.authRepo
    val locked by appLock.locked.collectAsStateWithLifecycle()
    val nav = rememberNavController()
    // The route the app opened on, null while a cold-start lock is up. Saved, so a rotation
    // rebuilds the same graph (and the NavController its back stack).
    var startRoute by rememberSaveable { mutableStateOf(if (appLock.locked.value) null else startRouteFor(auth)) }

    fun toLogin() {
        if (startRoute == null) {
            startRoute = Routes.LOGIN
        } else {
            nav.navigate(Routes.LOGIN) {
                popUpTo(0) { inclusive = true }
                launchSingleTop = true
            }
        }
    }

    fun onLockOutcome(outcome: LockOutcome) {
        when (outcome) {
            is LockOutcome.Unlocked -> {
                appLock.unlock()
                if (startRoute == null) {
                    startRoute = startRouteFor(auth)
                } else if (outcome.mustChange && nav.currentDestination?.route != Routes.CHANGE_PASSWORD) {
                    nav.navigate(Routes.CHANGE_PASSWORD) {
                        popUpTo(0) { inclusive = true }
                        launchSingleTop = true
                    }
                }
            }
            is LockOutcome.UsePassword -> {
                auth.leaveSession()
                container.loginHandoff.post(outcome.identifier, outcome.notice)
                appLock.unlock()
                toLogin()
            }
            LockOutcome.SwitchAccount -> {
                auth.leaveSession()
                appLock.unlock()
                toLogin()
            }
        }
    }

    // Belt and braces: whatever unlocked the app, it is shown.
    LaunchedEffect(locked) {
        if (!locked && startRoute == null) startRoute = startRouteFor(auth)
    }

    // The silent refresh was refused (or there was nothing to refresh with): back to the
    // login screen, which says why. Nothing is signed in any more, so there is nothing for
    // a lock to cover.
    LaunchedEffect(Unit) {
        container.authExpired.collect {
            appLock.unlock()
            toLogin()
        }
    }

    Box(Modifier.fillMaxSize()) {
        startRoute?.let { route ->
            // While locked, the screen underneath is hidden from accessibility services too.
            Box(Modifier.fillMaxSize().then(if (locked) Modifier.clearAndSetSemantics { } else Modifier)) {
                AppNav(navController = nav, startRoute = route, container = container, gate = gate)
            }
        }
        if (locked) {
            LockGate(container = container, gate = gate, onOutcome = ::onLockOutcome, onBack = onExit)
        }
    }
}

/** Where a session as stored opens: the login screen, the forced password change, or Home. */
private fun startRouteFor(auth: AuthRepository): String = when {
    !auth.isLoggedIn -> Routes.LOGIN
    auth.forcePasswordChange -> Routes.CHANGE_PASSWORD
    else -> Routes.HOME
}
