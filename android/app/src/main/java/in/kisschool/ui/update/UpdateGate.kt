package `in`.kisschool.ui.update

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.lifecycle.ViewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewModelScope
import androidx.lifecycle.viewmodel.compose.viewModel
import `in`.kisschool.data.repo.AppUpdateRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch

data class UpdateUiState(
    /** Installed build is below the published minimum → app is blocked until updated. */
    val forced: Boolean = false,
    /** A newer build exists but the current one is still allowed → soft prompt. */
    val optional: Boolean = false,
    val latestName: String? = null,
    val apkUrl: String? = null,
)

class UpdateViewModel(private val repo: AppUpdateRepository) : ViewModel() {
    private val _state = MutableStateFlow(UpdateUiState())
    val state = _state.asStateFlow()

    init { check() }

    private fun check() {
        viewModelScope.launch {
            val m = repo.fetch() ?: return@launch  // fail open
            val installed = repo.installedVersionCode
            _state.value = UpdateUiState(
                forced = m.minVersionCode > installed,
                optional = m.minVersionCode <= installed && m.latestVersionCode > installed,
                latestName = m.latestVersionName,
                apkUrl = m.apkUrl,
            )
        }
    }
}

/**
 * Wraps the app content and overlays an update prompt when the published manifest
 * says this build is out of date. A forced update is a full-screen, non-dismissable
 * [Dialog] (no back-press escape) — the app is unusable until the teacher installs
 * the new APK.
 */
@Composable
fun UpdateGate(repo: AppUpdateRepository, content: @Composable () -> Unit) {
    val vm: UpdateViewModel = viewModel { UpdateViewModel(repo) }
    val s by vm.state.collectAsStateWithLifecycle()
    var optionalDismissed by remember { mutableStateOf(false) }
    val ctx = LocalContext.current

    content()

    when {
        s.forced -> ForcedUpdateOverlay(
            latestName = s.latestName,
            onUpdate = { openInBrowser(ctx, s.apkUrl) },
        )
        s.optional && !optionalDismissed -> OptionalUpdateDialog(
            latestName = s.latestName,
            onUpdate = { openInBrowser(ctx, s.apkUrl) },
            onLater = { optionalDismissed = true },
        )
    }
}

@Composable
private fun ForcedUpdateOverlay(latestName: String?, onUpdate: () -> Unit) {
    Dialog(
        onDismissRequest = { /* forced: cannot be dismissed */ },
        properties = DialogProperties(
            dismissOnBackPress = false,
            dismissOnClickOutside = false,
            usePlatformDefaultWidth = false,
        ),
    ) {
        Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
            Column(
                Modifier
                    .fillMaxSize()
                    .padding(28.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.Center,
            ) {
                Text(
                    "Update required",
                    style = MaterialTheme.typography.headlineSmall,
                    color = MaterialTheme.colorScheme.primary,
                )
                Text(
                    buildString {
                        append("A newer version of KIS Attendance is available")
                        if (!latestName.isNullOrBlank()) append(" (v$latestName)")
                        append(". Please update to continue using the app.")
                    },
                    style = MaterialTheme.typography.bodyMedium,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 12.dp, bottom = 24.dp),
                )
                Button(onClick = onUpdate, modifier = Modifier.fillMaxWidth()) {
                    Text("Download update")
                }
                Text(
                    "After downloading, open the file to install over the current app.",
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 16.dp),
                )
            }
        }
    }
}

@Composable
private fun OptionalUpdateDialog(
    latestName: String?,
    onUpdate: () -> Unit,
    onLater: () -> Unit,
) {
    AlertDialog(
        onDismissRequest = onLater,
        title = { Text("Update available") },
        text = {
            Text(
                buildString {
                    append("A newer version")
                    if (!latestName.isNullOrBlank()) append(" (v$latestName)")
                    append(" is available. Update now for the latest fixes.")
                }
            )
        },
        confirmButton = { TextButton(onClick = onUpdate) { Text("Update") } },
        dismissButton = { TextButton(onClick = onLater) { Text("Later") } },
    )
}

private fun openInBrowser(ctx: Context, url: String?) {
    val target = url?.takeIf { it.isNotBlank() } ?: return
    try {
        ctx.startActivity(
            Intent(Intent.ACTION_VIEW, Uri.parse(target)).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
        )
    } catch (_: Exception) {
        // No browser / bad url — nothing else we can do from here.
    }
}
