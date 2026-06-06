package `in`.kisschool.ui.nav

import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import `in`.kisschool.di.AppContainer
import `in`.kisschool.ui.screens.attendance.AttendanceScreen
import `in`.kisschool.ui.screens.attendance.AttendanceViewModel
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
import `in`.kisschool.ui.screens.studentdetail.StudentDetailScreen
import `in`.kisschool.ui.screens.studentdetail.StudentDetailViewModel
import `in`.kisschool.ui.screens.studentedit.EditStudentScreen
import `in`.kisschool.ui.screens.studentedit.EditStudentViewModel
import `in`.kisschool.ui.screens.students.StudentsScreen
import `in`.kisschool.ui.screens.students.StudentsViewModel

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
    const val FORGOT_PASSWORD = "forgot-password"
    fun studentDetail(id: Long) = "student/$id"
    fun studentEdit(id: Long) = "student/$id/edit"
    // Attendance pre-set to a (class, date) — used by the dashboard calendar tap-through.
    fun attendanceFor(className: String, iso: String) =
        "$ATTENDANCE?class=${Uri.encode(className)}&date=$iso"
}

@Composable
fun AppNav(navController: NavHostController, startRoute: String, container: AppContainer) {
    NavHost(navController = navController, startDestination = startRoute) {

        composable(Routes.LOGIN) {
            val vm = viewModel { LoginViewModel(container.authRepo) }
            LoginScreen(
                vm = vm,
                onLoggedIn = { mustChange ->
                    val target = if (mustChange) Routes.CHANGE_PASSWORD else Routes.HOME
                    navController.navigate(target) {
                        popUpTo(Routes.LOGIN) { inclusive = true }
                    }
                },
                onForgotPassword = { navController.navigate(Routes.FORGOT_PASSWORD) }
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
                    allowedClasses = container.authRepo.allowedClasses
                )
            }
            // Refresh the coverage calendar when returning from a save on the
            // Attendance screen (same savedStateHandle pattern as students_changed).
            val attChanged by entry.savedStateHandle
                .getStateFlow("attendance_changed", false)
                .collectAsStateWithLifecycle()
            LaunchedEffect(attChanged) {
                if (attChanged) {
                    dashVm.reloadCurrentMonth()
                    entry.savedStateHandle["attendance_changed"] = false
                }
            }
            HomeScreen(
                userName = container.authRepo.displayName ?: "Teacher",
                dashVm = dashVm,
                onOpenAttendanceFor = { c, iso -> navController.navigate(Routes.attendanceFor(c, iso)) },
                onTakeAttendance = { navController.navigate(Routes.ATTENDANCE) },
                onViewHistory = { navController.navigate(Routes.HISTORY) },
                onViewStudents = { navController.navigate(Routes.STUDENTS) },
                onMarksEntry = { navController.navigate(Routes.MARKS) },
                onLogout = {
                    container.authRepo.logout()
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }

        composable(Routes.MARKS) {
            val vm = viewModel {
                MarksEntryViewModel(
                    studentRepo = container.studentRepo,
                    marksRepo = container.marksRepo,
                    allowedClasses = container.authRepo.allowedClasses
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
            // Optional args (default "") → the plain "attendance" tile route still matches
            // and falls back to first class + today.
            val initClass = entry.arguments?.getString("class")?.ifBlank { null }
            val initDate = entry.arguments?.getString("date")?.ifBlank { null }
            val vm = viewModel {
                AttendanceViewModel(
                    studentRepo = container.studentRepo,
                    attendanceRepo = container.attendanceRepo,
                    allowedClasses = container.authRepo.allowedClasses,
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
                },
            )
        }

        composable(Routes.HISTORY) {
            val vm = viewModel {
                HistoryViewModel(
                    studentRepo = container.studentRepo,
                    attendanceRepo = container.attendanceRepo,
                    allowedClasses = container.authRepo.allowedClasses
                )
            }
            HistoryScreen(vm = vm, onBack = { navController.popBackStack() })
        }

        composable(Routes.STUDENTS) { entry ->
            val vm = viewModel {
                StudentsViewModel(
                    studentRepo = container.studentRepo,
                    allowedClasses = container.authRepo.allowedClasses
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
                    authToken = container.tokenStore.token
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
