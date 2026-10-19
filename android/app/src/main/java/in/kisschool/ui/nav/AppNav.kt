package `in`.kisschool.ui.nav

import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavBackStackEntry
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import `in`.kisschool.data.repo.AuthRepository
import `in`.kisschool.data.repo.MenuKeys
import `in`.kisschool.di.AppContainer
import `in`.kisschool.ui.lock.BiometricGate
import `in`.kisschool.ui.screens.approvals.ApprovalsScreen
import `in`.kisschool.ui.screens.approvals.ApprovalsViewModel
import `in`.kisschool.ui.screens.attendance.AttendanceScreen
import `in`.kisschool.ui.screens.attendance.AttendanceViewModel
import `in`.kisschool.ui.screens.classestoday.ClassesTodayScreen
import `in`.kisschool.ui.screens.classestoday.ClassesTodayViewModel
import `in`.kisschool.ui.screens.dashboard.ClassDayKind
import `in`.kisschool.ui.screens.dashboard.DashboardAccess
import `in`.kisschool.ui.screens.dashboard.DashboardViewModel
import `in`.kisschool.ui.screens.history.HistoryScreen
import `in`.kisschool.ui.screens.history.HistoryViewModel
import `in`.kisschool.ui.screens.home.HomeScreen
import `in`.kisschool.ui.screens.login.ChangePasswordScreen
import `in`.kisschool.ui.screens.login.ChangePasswordViewModel
import `in`.kisschool.ui.screens.login.ForgotPasswordScreen
import `in`.kisschool.ui.screens.login.ForgotPasswordViewModel
import `in`.kisschool.ui.screens.login.LoginScreen
import `in`.kisschool.ui.screens.login.LoginViewModel
import `in`.kisschool.ui.screens.marks.MarksEntryScreen
import `in`.kisschool.ui.screens.marks.MarksEntryViewModel
import `in`.kisschool.ui.screens.notices.NoticesScreen
import `in`.kisschool.ui.screens.notices.NoticesViewModel
import `in`.kisschool.ui.screens.results.ReportCardPreviewScreen
import `in`.kisschool.ui.screens.results.ResultsScreen
import `in`.kisschool.ui.screens.results.ResultsViewModel
import `in`.kisschool.ui.screens.settings.SettingsScreen
import `in`.kisschool.ui.screens.settings.SettingsViewModel
import `in`.kisschool.ui.screens.studentdetail.StudentDetailScreen
import `in`.kisschool.ui.screens.studentdetail.StudentDetailViewModel
import `in`.kisschool.ui.screens.studentedit.EditStudentScreen
import `in`.kisschool.ui.screens.studentedit.EditStudentViewModel
import `in`.kisschool.ui.screens.students.StudentsScreen
import `in`.kisschool.ui.screens.students.StudentsViewModel
import java.time.LocalDate

object Routes {
    const val LOGIN = "login"
    const val CHANGE_PASSWORD = "change-password"
    const val HOME = "home"
    const val ATTENDANCE = "attendance"
    const val HISTORY = "history"
    const val STUDENTS = "students"
    const val STUDENT_DETAIL = "student/{id}"
    const val STUDENT_EDIT = "student/{id}/edit"
    const val MARKS = "marks"
    const val APPROVALS = "approvals"
    const val FORGOT_PASSWORD = "forgot-password"
    const val RESULTS = "results"
    const val NOTICES = "notices"
    /** Theme, the app lock and the account's signed-in devices (the drawer's Settings). */
    const val SETTINGS = "settings"
    /** One day's marked / pending / holiday classes, opened from the dashboard's classes ring. */
    const val CLASSES_TODAY = "classes-today/{kind}?date={date}"
    fun classesToday(kind: ClassDayKind, iso: String) = "classes-today/${kind.key}?date=$iso"
    // Results, Marks entry and Students opened on a class (a dashboard row); the plain route
    // (the drawer's) still matches, with no class.
    fun resultsFor(className: String) = "$RESULTS?class=${Uri.encode(className)}"
    fun marksFor(className: String) = "$MARKS?class=${Uri.encode(className)}"
    fun studentsFor(className: String) = "$STUDENTS?class=${Uri.encode(className)}"
    const val REPORT_CARD = "report-card/{studentId}?name={name}"
    fun reportCard(studentId: Long, name: String) = "report-card/$studentId?name=${Uri.encode(name)}"
    fun studentDetail(id: Long) = "student/$id"
    fun studentEdit(id: Long) = "student/$id/edit"
    // Attendance pre-set to a (class, date) — used by the dashboard calendar tap-through.
    fun attendanceFor(className: String, iso: String) =
        "$ATTENDANCE?class=${Uri.encode(className)}&date=$iso"
}

@Composable
fun AppNav(
    navController: NavHostController,
    startRoute: String,
    container: AppContainer,
    /** The phone's fingerprint / face / PIN prompt (saved accounts, Settings → App lock). */
    gate: BiometricGate,
) {
    /** Back to the login screen with nothing behind it (after Logout or Switch account). */
    fun toLogin() {
        navController.navigate(Routes.LOGIN) {
            popUpTo(0) { inclusive = true }
            launchSingleTop = true
        }
    }

    NavHost(navController = navController, startDestination = startRoute) {

        composable(Routes.LOGIN) {
            val vm = viewModel {
                LoginViewModel(
                    auth = container.authRepo,
                    settings = container.settings,
                    canUseBiometrics = gate::canUse,
                    // Why the app came here (an expired sign-in) and whose password it needs.
                    handoff = container.loginHandoff.take(),
                )
            }
            LoginScreen(
                vm = vm,
                gate = gate,
                onLoggedIn = { mustChange ->
                    val target = if (mustChange) Routes.CHANGE_PASSWORD else Routes.HOME
                    navController.navigate(target) {
                        popUpTo(0) { inclusive = true }
                    }
                },
                onForgotPassword = { navController.navigate(Routes.FORGOT_PASSWORD) }
            )
        }

        composable(Routes.SETTINGS) {
            val vm = viewModel { SettingsViewModel(container.authRepo, container.settings) }
            SettingsScreen(
                vm = vm,
                gate = gate,
                onBack = { navController.popBackStack() },
                onSignedOut = ::toLogin,
            )
        }

        composable(Routes.FORGOT_PASSWORD) {
            val vm = viewModel { ForgotPasswordViewModel(container.authRepo) }
            ForgotPasswordScreen(
                vm = vm,
                onBack = { navController.popBackStack() }
            )
        }

        composable(Routes.CHANGE_PASSWORD) {
            val vm = viewModel { ChangePasswordViewModel(container.authRepo) }
            ChangePasswordScreen(
                vm = vm,
                onDone = {
                    navController.navigate(Routes.HOME) {
                        popUpTo(Routes.CHANGE_PASSWORD) { inclusive = true }
                    }
                }
            )
        }

        composable(Routes.HOME) { entry ->
            val dashVm = viewModel {
                DashboardViewModel(
                    attendanceRepo = container.attendanceRepo,
                    dashboardRepo = container.dashboardRepo,
                    sessionRepo = container.sessionRepo,
                    noticeRepo = container.noticeRepo,
                    resultsRepo = container.resultsRepo,
                    allowedClasses = container.authRepo.visibleClasses,
                    access = dashboardAccess(container.authRepo),
                )
            }
            // Attendance saved on the Attendance screen (opened from here or from a list of
            // classes): the attendance cards and the open month reload (same savedStateHandle
            // pattern as students_changed).
            val attChanged by entry.savedStateHandle
                .getStateFlow("attendance_changed", false)
                .collectAsStateWithLifecycle()
            LaunchedEffect(attChanged) {
                if (attChanged) {
                    dashVm.onAttendanceChanged()
                    entry.savedStateHandle["attendance_changed"] = false
                }
            }
            // Back on Home (or the app reopened): stale cards and the approval counts reload.
            LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { dashVm.onResumed() }
            // Hydrate role on home open so the Approvals drawer item appears for
            // super-admins even on installs that logged in before the app stored role
            // (refreshMe is best-effort; failure leaves role as-is → item stays hidden).
            // Menu grants (allowed_menus) refresh the same way, gating the Marks and
            // Results items (admins and super-admins always see both), and so do the
            // name and role chip in the header and the dashboard's class list: an admin
            // whose role arrives late still gets every class.
            var isSuperAdmin by remember { mutableStateOf(container.authRepo.isSuperAdmin) }
            var canMarksEntry by remember { mutableStateOf(container.authRepo.canAccess(MenuKeys.MARKS_ENTRY)) }
            var canResults by remember { mutableStateOf(container.authRepo.canAccess(MenuKeys.MARKS_RESULTS)) }
            var userName by remember { mutableStateOf(container.authRepo.displayName.orEmpty()) }
            var role by remember { mutableStateOf(container.authRepo.role) }
            LaunchedEffect(Unit) {
                runCatching { container.authRepo.refreshMe() }
                isSuperAdmin = container.authRepo.isSuperAdmin
                canMarksEntry = container.authRepo.canAccess(MenuKeys.MARKS_ENTRY)
                canResults = container.authRepo.canAccess(MenuKeys.MARKS_RESULTS)
                userName = container.authRepo.displayName.orEmpty()
                role = container.authRepo.role
                dashVm.configure(container.authRepo.visibleClasses, dashboardAccess(container.authRepo))
            }
            HomeScreen(
                userName = userName,
                role = role,
                dashVm = dashVm,
                onOpenAttendanceFor = { c, iso -> navController.navigate(Routes.attendanceFor(c, iso)) },
                onOpenClassesToday = { kind, iso -> navController.navigate(Routes.classesToday(kind, iso)) },
                onTakeAttendance = { navController.navigate(Routes.ATTENDANCE) },
                onViewHistory = { navController.navigate(Routes.HISTORY) },
                onViewStudents = { navController.navigate(Routes.STUDENTS) },
                onStudentsFor = { c -> navController.navigate(if (c == null) Routes.STUDENTS else Routes.studentsFor(c)) },
                onMarksEntry = { navController.navigate(Routes.MARKS) },
                onMarksEntryFor = { c -> navController.navigate(if (c == null) Routes.MARKS else Routes.marksFor(c)) },
                onResultsFor = { c -> navController.navigate(if (c == null) Routes.RESULTS else Routes.resultsFor(c)) },
                onNotices = { navController.navigate(Routes.NOTICES) },
                onLogout = {
                    container.authRepo.logout()
                    toLogin()
                },
                // Only a session saved on this phone can be switched back to (a server
                // without device sessions keeps the old one-hour sign-in).
                canSwitchAccount = container.authRepo.activeAccount != null,
                onSwitchAccount = {
                    container.authRepo.leaveSession()
                    toLogin()
                },
                onSettings = { navController.navigate(Routes.SETTINGS) },
                isSuperAdmin = isSuperAdmin,
                onApprovals = { navController.navigate(Routes.APPROVALS) },
                canMarksEntry = canMarksEntry,
                canResults = canResults,
                onResults = { navController.navigate(Routes.RESULTS) },
            )
        }

        composable(
            route = "${Routes.RESULTS}?class={class}",
            arguments = listOf(navArgument("class") { type = NavType.StringType; defaultValue = "" }),
        ) { entry ->
            val initClass = entry.classArg()
            val vm = viewModel {
                ResultsViewModel(
                    resultsRepo = container.resultsRepo,
                    sessionRepo = container.sessionRepo,
                    reportCardRepo = container.reportCardRepo,
                    classOptions = container.authRepo.visibleClasses,
                    initialClass = initClass,
                )
            }
            ResultsScreen(
                vm = vm,
                onBack = { navController.popBackStack() },
                onOpenReportCard = { id, name -> navController.navigate(Routes.reportCard(id, name)) },
            )
        }

        composable(
            route = Routes.REPORT_CARD,
            arguments = listOf(
                navArgument("studentId") { type = NavType.LongType },
                navArgument("name") { type = NavType.StringType; defaultValue = "" },
            )
        ) { entry ->
            val id = entry.arguments?.getLong("studentId") ?: 0L
            val name = entry.arguments?.getString("name").orEmpty()
            // Looked up once: the card keeps the server's file name, so finding it lists a folder.
            val file = remember(id) { container.reportCardRepo.fileFor(id) }
            ReportCardPreviewScreen(
                file = file,
                studentName = name,
                warnings = container.reportCardRepo.warningsFor(id),
                onBack = { navController.popBackStack() },
            )
        }

        composable(Routes.APPROVALS) {
            val vm = viewModel { ApprovalsViewModel(container.adminRepo) }
            ApprovalsScreen(vm = vm, onBack = { navController.popBackStack() })
        }

        // Read-only notice board; every signed-in user may read it.
        composable(Routes.NOTICES) {
            val vm = viewModel { NoticesViewModel(container.noticeRepo) }
            NoticesScreen(vm = vm, onBack = { navController.popBackStack() })
        }

        // One day's marked / pending / holiday classes (the dashboard's classes ring).
        composable(
            route = Routes.CLASSES_TODAY,
            arguments = listOf(
                navArgument("kind") { type = NavType.StringType },
                navArgument("date") { type = NavType.StringType; defaultValue = "" },
            )
        ) { entry ->
            val kind = ClassDayKind.of(entry.arguments?.getString("kind"))
            val date = entry.arguments?.getString("date")
                ?.let { runCatching { LocalDate.parse(it) }.getOrNull() }
                ?: LocalDate.now()
            val vm = viewModel { ClassesTodayViewModel(container.dashboardRepo, kind, date) }
            // A register saved from this list: fetch the day again, so the class moves lists.
            val attChanged by entry.savedStateHandle
                .getStateFlow("attendance_changed", false)
                .collectAsStateWithLifecycle()
            LaunchedEffect(attChanged) {
                if (attChanged) {
                    vm.load()
                    entry.savedStateHandle["attendance_changed"] = false
                }
            }
            ClassesTodayScreen(
                vm = vm,
                onBack = { navController.popBackStack() },
                onOpenAttendance = { c, iso -> navController.navigate(Routes.attendanceFor(c, iso)) },
            )
        }

        composable(
            route = "${Routes.MARKS}?class={class}",
            arguments = listOf(navArgument("class") { type = NavType.StringType; defaultValue = "" }),
        ) { entry ->
            val initClass = entry.classArg()
            val vm = viewModel {
                MarksEntryViewModel(
                    studentRepo = container.studentRepo,
                    marksRepo = container.marksRepo,
                    sessionRepo = container.sessionRepo,
                    metaRepo = container.metaRepo,
                    classOptions = container.authRepo.visibleClasses,
                    isSuperAdmin = container.authRepo.isSuperAdmin,
                    initialClass = initClass,
                )
            }
            MarksEntryScreen(vm = vm, onBack = { navController.popBackStack() })
        }

        composable(
            route = "${Routes.ATTENDANCE}?class={class}&date={date}",
            arguments = listOf(
                navArgument("class") { type = NavType.StringType; defaultValue = "" },
                navArgument("date") { type = NavType.StringType; defaultValue = "" },
            )
        ) { entry ->
            // Optional args (default "") → the plain "attendance" route (the drawer's Take
            // attendance) still matches and falls back to first class + today.
            val initClass = entry.arguments?.getString("class")?.ifBlank { null }
            val initDate = entry.arguments?.getString("date")?.ifBlank { null }
            val vm = viewModel {
                AttendanceViewModel(
                    studentRepo = container.studentRepo,
                    attendanceRepo = container.attendanceRepo,
                    allowedClasses = container.authRepo.visibleClasses,
                    initialClass = initClass,
                    initialDate = initDate,
                )
            }
            AttendanceScreen(
                vm = vm,
                onBack = { navController.popBackStack() },
                onSaved = {
                    navController.previousBackStackEntry
                        ?.savedStateHandle?.set("attendance_changed", true)
                    // Home too, when the register was opened from a list of classes on top of it.
                    runCatching { navController.getBackStackEntry(Routes.HOME) }.getOrNull()
                        ?.savedStateHandle?.set("attendance_changed", true)
                },
            )
        }

        composable(Routes.HISTORY) {
            val vm = viewModel {
                HistoryViewModel(
                    studentRepo = container.studentRepo,
                    attendanceRepo = container.attendanceRepo,
                    allowedClasses = container.authRepo.visibleClasses
                )
            }
            HistoryScreen(vm = vm, onBack = { navController.popBackStack() })
        }

        composable(
            route = "${Routes.STUDENTS}?class={class}",
            arguments = listOf(navArgument("class") { type = NavType.StringType; defaultValue = "" }),
        ) { entry ->
            val initClass = entry.classArg()
            val vm = viewModel {
                StudentsViewModel(
                    studentRepo = container.studentRepo,
                    allowedClasses = container.authRepo.visibleClasses,
                    initialClass = initClass,
                )
            }
            // The detail screen flags this when a deletion is requested, so the
            // list re-fetches and shows the new pending-delete status on return.
            val changed by entry.savedStateHandle
                .getStateFlow("students_changed", false)
                .collectAsStateWithLifecycle()
            LaunchedEffect(changed) {
                if (changed) {
                    vm.refresh()
                    entry.savedStateHandle["students_changed"] = false
                }
            }
            StudentsScreen(
                vm = vm,
                onOpenStudent = { id -> navController.navigate(Routes.studentDetail(id)) },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.STUDENT_DETAIL,
            arguments = listOf(navArgument("id") { type = NavType.LongType })
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            val vm = viewModel {
                StudentDetailViewModel(
                    studentRepo = container.studentRepo,
                    studentId = id,
                    allowedClasses = container.authRepo.allowedClasses
                )
            }
            // When the edit screen pops back with a success result, refresh so the
            // pending-approval lock reflects the just-submitted edit.
            val edited by entry.savedStateHandle
                .getStateFlow("student_edited", false)
                .collectAsStateWithLifecycle()
            LaunchedEffect(edited) {
                if (edited) {
                    vm.reload()
                    entry.savedStateHandle["student_edited"] = false
                }
            }
            StudentDetailScreen(
                vm = vm,
                onEdit = { navController.navigate(Routes.studentEdit(id)) },
                onDeleted = {
                    // Tell the students list to refresh so the new pending-delete
                    // status shows, then return to it.
                    navController.previousBackStackEntry
                        ?.savedStateHandle?.set("students_changed", true)
                    navController.popBackStack()
                },
                onBack = { navController.popBackStack() }
            )
        }

        composable(
            route = Routes.STUDENT_EDIT,
            arguments = listOf(navArgument("id") { type = NavType.LongType })
        ) { entry ->
            val id = entry.arguments?.getLong("id") ?: 0L
            val vm = viewModel {
                EditStudentViewModel(
                    studentRepo = container.studentRepo,
                    studentId = id,
                    allowedClasses = container.authRepo.allowedClasses,
                )
            }
            EditStudentScreen(
                vm = vm,
                onSaved = {
                    navController.previousBackStackEntry
                        ?.savedStateHandle?.set("student_edited", true)
                    navController.popBackStack()
                },
                onBack = { navController.popBackStack() }
            )
        }
    }
}

/** What the dashboard shows this user: their role and the two marks menu grants. */
private fun dashboardAccess(auth: AuthRepository) = DashboardAccess(
    role = auth.role,
    canMarksEntry = auth.canAccess(MenuKeys.MARKS_ENTRY),
    canResults = auth.canAccess(MenuKeys.MARKS_RESULTS),
)

/** An optional class argument of a route ("" when the route was opened without one). */
private fun NavBackStackEntry.classArg(): String? = arguments?.getString("class")?.ifBlank { null }
