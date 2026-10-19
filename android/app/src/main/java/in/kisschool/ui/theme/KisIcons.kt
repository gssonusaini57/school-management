package `in`.kisschool.ui.theme

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Grading
import androidx.compose.material.icons.automirrored.outlined.Logout
import androidx.compose.material.icons.automirrored.outlined.Rule
import androidx.compose.material.icons.outlined.AccountCircle
import androidx.compose.material.icons.outlined.Badge
import androidx.compose.material.icons.outlined.BrightnessMedium
import androidx.compose.material.icons.outlined.Campaign
import androidx.compose.material.icons.outlined.Close
import androidx.compose.material.icons.outlined.Computer
import androidx.compose.material.icons.outlined.CurrencyRupee
import androidx.compose.material.icons.outlined.EditNote
import androidx.compose.material.icons.outlined.EventAvailable
import androidx.compose.material.icons.outlined.EventBusy
import androidx.compose.material.icons.outlined.Fingerprint
import androidx.compose.material.icons.outlined.Groups
import androidx.compose.material.icons.outlined.History
import androidx.compose.material.icons.outlined.HowToReg
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.outlined.Lock
import androidx.compose.material.icons.outlined.NotificationImportant
import androidx.compose.material.icons.outlined.Payments
import androidx.compose.material.icons.outlined.PendingActions
import androidx.compose.material.icons.outlined.PersonOff
import androidx.compose.material.icons.outlined.PhoneAndroid
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.SpaceDashboard
import androidx.compose.material.icons.outlined.SwitchAccount
import androidx.compose.material.icons.outlined.TaskAlt
import androidx.compose.material.icons.outlined.Timelapse
import androidx.compose.material.icons.outlined.WorkspacePremium
import androidx.compose.ui.graphics.vector.ImageVector

/**
 * The app's icons in one place, so the drawer, the screen titles and the dashboard cards
 * always show the same icon for the same thing. Outlined throughout; Grading, Rule and
 * Logout are the auto-mirrored outlined versions (the plain ones are deprecated).
 */
object KisIcons {
    // ── Screens (drawer items and screen titles) ──
    val Dashboard: ImageVector get() = Icons.Outlined.SpaceDashboard
    val TakeAttendance: ImageVector get() = Icons.Outlined.EventAvailable
    val PastAttendance: ImageVector get() = Icons.Outlined.History
    val Students: ImageVector get() = Icons.Outlined.Groups
    val MarksEntry: ImageVector get() = Icons.AutoMirrored.Outlined.Grading
    val Results: ImageVector get() = Icons.Outlined.WorkspacePremium
    val Approvals: ImageVector get() = Icons.AutoMirrored.Outlined.Rule
    val Notices: ImageVector get() = Icons.Outlined.Campaign
    val Fees: ImageVector get() = Icons.Outlined.CurrencyRupee
    val Staff: ImageVector get() = Icons.Outlined.Badge
    val Settings: ImageVector get() = Icons.Outlined.Settings
    val Theme: ImageVector get() = Icons.Outlined.BrightnessMedium
    val About: ImageVector get() = Icons.Outlined.Info
    val SwitchAccount: ImageVector get() = Icons.Outlined.SwitchAccount
    val Logout: ImageVector get() = Icons.AutoMirrored.Outlined.Logout

    // ── Accounts, app lock and signed-in devices ──
    val Account: ImageVector get() = Icons.Outlined.AccountCircle
    val AppLock: ImageVector get() = Icons.Outlined.Fingerprint
    val PhoneDevice: ImageVector get() = Icons.Outlined.PhoneAndroid
    val WebDevice: ImageVector get() = Icons.Outlined.Computer
    val Remove: ImageVector get() = Icons.Outlined.Close

    // ── Dashboard KPIs ──
    val Present: ImageVector get() = Icons.Outlined.HowToReg
    val Absent: ImageVector get() = Icons.Outlined.PersonOff
    val Leave: ImageVector get() = Icons.Outlined.EventBusy
    val HalfDay: ImageVector get() = Icons.Outlined.Timelapse
    val ClassesMarked: ImageVector get() = Icons.Outlined.TaskAlt
    val NotMarked: ImageVector get() = Icons.Outlined.PendingActions
    val Drafts: ImageVector get() = Icons.Outlined.EditNote
    val Submitted: ImageVector get() = Icons.Outlined.Lock
    val FeesCollected: ImageVector get() = Icons.Outlined.Payments
    val StudentsCount: ImageVector get() = Icons.Outlined.Groups
    val PendingApprovals: ImageVector get() = Icons.Outlined.NotificationImportant
}
