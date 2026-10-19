package `in`.kisschool.ui.screens.settings

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.selection.toggleable
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.DeviceSessionDto
import `in`.kisschool.data.settings.ThemeMode
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import `in`.kisschool.ui.components.ModuleIconCircle
import `in`.kisschool.ui.lock.BiometricGate
import `in`.kisschool.ui.theme.KisIcons
import `in`.kisschool.ui.theme.kisTopAppBarColors
import `in`.kisschool.util.formatDateTime
import `in`.kisschool.util.parseServerInstant
import `in`.kisschool.util.relativeAge
import java.time.Instant

/**
 * The drawer's Settings: the theme (applies at once, app-wide), the phone-wide App lock
 * (turning it on asks for the fingerprint, face or PIN first, so it is never switched on
 * where it can't be opened; off needs nothing), and the account's signed-in devices with a
 * sign-out for each. Signing "This phone" out is a Logout, so it lands on the login screen.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    vm: SettingsViewModel,
    gate: BiometricGate,
    onBack: () -> Unit,
    /** This phone was signed out from the devices list. */
    onSignedOut: () -> Unit,
) {
    val s by vm.state.collectAsStateWithLifecycle()
    val themeMode by vm.themeMode.collectAsStateWithLifecycle()
    val appLock by vm.appLock.collectAsStateWithLifecycle()

    // Whether the phone has a fingerprint, face or screen lock to ask for; checked again on
    // return from the phone's own settings, where one may just have been set up.
    var canUseLock by remember { mutableStateOf(gate.canUse()) }
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) { canUseLock = gate.canUse() }
    var prompting by remember { mutableStateOf(false) }

    LaunchedEffect(s.signedOut) {
        if (s.signedOut) onSignedOut()
    }

    fun toggleAppLock(on: Boolean) {
        if (!on) {
            vm.turnOffAppLock()
            return
        }
        if (prompting) return
        prompting = true
        gate.authenticate(subtitle = vm.accountName) { result ->
            prompting = false
            vm.onEnableResult(result)
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Settings", maxLines = 1, overflow = TextOverflow.Ellipsis) },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                colors = kisTopAppBarColors(),
            )
        }
    ) { padding ->
        LazyColumn(
            Modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp),
        ) {
            item(key = "appearance") {
                SettingsSection(title = "Theme") {
                    ThemeChoices(current = themeMode, onSelect = vm::setThemeMode)
                }
            }
            item(key = "security") {
                SettingsSection(title = "Security") {
                    AppLockRow(
                        on = appLock,
                        // Off is always allowed; on needs something to unlock with.
                        enabled = !prompting && (appLock || canUseLock),
                        onToggle = ::toggleAppLock,
                    )
                    if (!appLock && !canUseLock) {
                        Text(
                            "Set up a fingerprint, face or screen lock in your phone's settings to use App lock.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                    ErrorBanner(s.lockMessage)
                }
            }
            item(key = "devices") {
                SettingsSection(
                    title = "Signed-in devices",
                    action = {
                        if (s.devicesUnavailable == null) {
                            IconButton(onClick = vm::loadDevices, enabled = !s.loadingDevices) {
                                Icon(Icons.Default.Refresh, contentDescription = "Refresh the devices")
                            }
                        }
                    },
                ) {
                    DevicesContent(
                        s = s,
                        onRetry = vm::loadDevices,
                        onSignOut = vm::askSignOut,
                    )
                }
            }
        }
    }

    s.confirmSignOut?.let { device ->
        AlertDialog(
            onDismissRequest = vm::cancelSignOut,
            title = { Text(if (device.isCurrent) "Sign out of this phone?" else "Sign out ${deviceLabel(device)}?") },
            text = {
                Text(
                    if (device.isCurrent) {
                        "This account will be removed from this phone and you'll need your password to sign in again."
                    } else {
                        "That device will need the password to sign in again."
                    }
                )
            },
            confirmButton = { TextButton(onClick = vm::confirmSignOut) { Text("Sign out") } },
            dismissButton = { TextButton(onClick = vm::cancelSignOut) { Text("Cancel") } },
        )
    }
}

@Composable
private fun SettingsSection(
    title: String,
    action: (@Composable () -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(start = 16.dp, end = 16.dp, top = 12.dp, bottom = 16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp),
        ) {
            Row(Modifier.heightIn(min = 40.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    title,
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold,
                    modifier = Modifier.weight(1f),
                )
                action?.invoke()
            }
            content()
        }
    }
}

private val ThemeMode.label: String
    get() = when (this) {
        ThemeMode.LIGHT -> "Light"
        ThemeMode.DARK -> "Dark"
        ThemeMode.SYSTEM -> "Same as phone"
    }

/** Picking a choice re-themes the app straight away, this screen included. */
@Composable
private fun ThemeChoices(current: ThemeMode, onSelect: (ThemeMode) -> Unit) {
    Column(Modifier.selectableGroup()) {
        ThemeMode.entries.forEach { mode ->
            Row(
                Modifier
                    .fillMaxWidth()
                    .heightIn(min = 48.dp)
                    .clip(RoundedCornerShape(8.dp))
                    .selectable(
                        selected = mode == current,
                        onClick = { onSelect(mode) },
                        role = Role.RadioButton,
                    )
                    .padding(horizontal = 4.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                RadioButton(selected = mode == current, onClick = null)
                Text(
                    mode.label,
                    style = MaterialTheme.typography.bodyLarge,
                    modifier = Modifier.padding(start = 12.dp),
                )
            }
        }
    }
}

@Composable
private fun AppLockRow(on: Boolean, enabled: Boolean, onToggle: (Boolean) -> Unit) {
    val fg = MaterialTheme.colorScheme.primary
    Row(
        Modifier
            .fillMaxWidth()
            .clip(RoundedCornerShape(8.dp))
            .toggleable(value = on, enabled = enabled, role = Role.Switch, onValueChange = onToggle)
            .padding(vertical = 6.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ModuleIconCircle(icon = KisIcons.AppLock, fg = fg, container = fg.copy(alpha = 0.12f), size = 40.dp)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text("App lock", style = MaterialTheme.typography.bodyLarge, fontWeight = FontWeight.Medium)
            Text(
                "Ask for your fingerprint, face or phone PIN when the app opens and after 15 minutes away. " +
                    "Applies to every account saved on this phone.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
        Spacer(Modifier.width(12.dp))
        // The row toggles; the switch only shows the state (no second touch target).
        Switch(checked = on, onCheckedChange = null, enabled = enabled)
    }
}

@Composable
private fun DevicesContent(
    s: SettingsUiState,
    onRetry: () -> Unit,
    onSignOut: (DeviceSessionDto) -> Unit,
) {
    Text(
        "Phones and browsers that stay signed in to your account. A device you sign out " +
            "needs the password to sign in again.",
        style = MaterialTheme.typography.bodySmall,
        color = MaterialTheme.colorScheme.onSurfaceVariant,
    )
    when {
        s.devicesUnavailable != null -> Text(
            s.devicesUnavailable,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        !s.devicesLoaded && s.loadingDevices -> LoadingRow()
        !s.devicesLoaded && s.devicesError != null -> {
            ErrorBanner(s.devicesError)
            OutlinedButton(onClick = onRetry) { Text("Try again") }
        }
        else -> {
            if (s.loadingDevices) LinearProgressIndicator(Modifier.fillMaxWidth())
            ErrorBanner(s.devicesError)
            if (s.devices.isEmpty()) {
                Text(
                    "No devices are signed in to your account.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            val now = Instant.now()
            s.devices.forEachIndexed { i, device ->
                if (i > 0) HorizontalDivider()
                DeviceRow(
                    device = device,
                    now = now,
                    signingOut = s.signingOutId == device.id,
                    enabled = s.signingOutId == null,
                    onSignOut = { onSignOut(device) },
                )
            }
        }
    }
}

/** The device's own name, or what kind of device it is when it sent none. */
private fun deviceLabel(device: DeviceSessionDto): String =
    device.deviceName.trim().ifBlank { if (device.platform == "web") "Web browser" else "Android phone" }

@Composable
private fun DeviceRow(
    device: DeviceSessionDto,
    now: Instant,
    signingOut: Boolean,
    enabled: Boolean,
    onSignOut: () -> Unit,
) {
    val muted = MaterialTheme.colorScheme.onSurfaceVariant
    val signedIn = parseServerInstant(device.createdAt)
    val lastActive = parseServerInstant(device.lastUsedAt)
    val details = buildList {
        add(if (device.platform == "web") "Website" else "Android app")
        signedIn?.let { add("signed in ${formatDateTime(it)}") }
        lastActive?.let { add("active ${relativeAge(it, now)}") }
    }.joinToString(" · ")
    Row(
        Modifier
            .fillMaxWidth()
            .padding(vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ModuleIconCircle(
            icon = if (device.platform == "web") KisIcons.WebDevice else KisIcons.PhoneDevice,
            fg = muted,
            container = muted.copy(alpha = 0.10f),
            size = 40.dp,
        )
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    deviceLabel(device),
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.Medium,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false),
                )
                if (device.isCurrent) ThisPhoneTag()
            }
            Text(details, style = MaterialTheme.typography.bodySmall, color = muted)
        }
        if (signingOut) {
            CircularProgressIndicator(Modifier.padding(horizontal = 12.dp).size(20.dp), strokeWidth = 2.dp)
        } else {
            TextButton(onClick = onSignOut, enabled = enabled) { Text("Sign out") }
        }
    }
}

@Composable
private fun ThisPhoneTag() {
    val c = MaterialTheme.colorScheme
    Text(
        "This phone",
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        color = c.onPrimaryContainer,
        maxLines = 1,
        modifier = Modifier
            .background(c.primaryContainer, RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 2.dp),
    )
}
