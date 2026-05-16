package com.expressonly.kisattendance.ui.nav

import androidx.compose.runtime.Composable
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.navArgument
import com.expressonly.kisattendance.di.AppContainer
import com.expressonly.kisattendance.ui.screens.attendance.AttendanceScreen
import com.expressonly.kisattendance.ui.screens.attendance.AttendanceViewModel
import com.expressonly.kisattendance.ui.screens.history.HistoryScreen
import com.expressonly.kisattendance.ui.screens.history.HistoryViewModel
import com.expressonly.kisattendance.ui.screens.home.HomeScreen
import com.expressonly.kisattendance.ui.screens.login.ChangePasswordScreen
import com.expressonly.kisattendance.ui.screens.login.ChangePasswordViewModel
import com.expressonly.kisattendance.ui.screens.login.LoginScreen
import com.expressonly.kisattendance.ui.screens.login.LoginViewModel
import com.expressonly.kisattendance.ui.screens.studentdetail.StudentDetailScreen
import com.expressonly.kisattendance.ui.screens.studentdetail.StudentDetailViewModel
import com.expressonly.kisattendance.ui.screens.students.StudentsScreen
import com.expressonly.kisattendance.ui.screens.students.StudentsViewModel

object Routes {
    const val LOGIN = "login"
    const val CHANGE_PASSWORD = "change-password"
    const val HOME = "home"
    const val ATTENDANCE = "attendance"
    const val HISTORY = "history"
    const val STUDENTS = "students"
    const val STUDENT_DETAIL = "student/{id}"
    fun studentDetail(id: Long) = "student/$id"
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
                }
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

        composable(Routes.HOME) {
            HomeScreen(
                userName = container.authRepo.displayName ?: "Teacher",
                onTakeAttendance = { navController.navigate(Routes.ATTENDANCE) },
                onViewHistory = { navController.navigate(Routes.HISTORY) },
                onViewStudents = { navController.navigate(Routes.STUDENTS) },
                onLogout = {
                    container.authRepo.logout()
                    navController.navigate(Routes.LOGIN) {
                        popUpTo(0) { inclusive = true }
                    }
                }
            )
        }

        composable(Routes.ATTENDANCE) {
            val vm = viewModel {
                AttendanceViewModel(
                    studentRepo = container.studentRepo,
                    attendanceRepo = container.attendanceRepo,
                    allowedClasses = container.authRepo.allowedClasses
                )
            }
            AttendanceScreen(vm = vm, onBack = { navController.popBackStack() })
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

        composable(Routes.STUDENTS) {
            val vm = viewModel {
                StudentsViewModel(
                    studentRepo = container.studentRepo,
                    allowedClasses = container.authRepo.allowedClasses
                )
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
            StudentDetailScreen(vm = vm, onBack = { navController.popBackStack() })
        }
    }
}
