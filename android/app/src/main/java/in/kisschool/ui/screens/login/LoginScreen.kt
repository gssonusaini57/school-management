package `in`.kisschool.ui.screens.login

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.BuildConfig
import `in`.kisschool.R
import `in`.kisschool.data.auth.SavedAccount
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.ModuleIconCircle
import `in`.kisschool.ui.components.RoleChip
import `in`.kisschool.ui.components.roleLabel
import `in`.kisschool.ui.lock.BiometricGate
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisIcons

/**
 * Sign-in: the accounts saved on this phone ("Saved on this phone": tap one to open it,
 * behind the app lock's prompt when that is on; × removes it), then the password form for
 * a new account or one whose saved sign-in has expired. After a password sign-in the phone's
 * own unlock is offered once per account ("Sign in faster next time?").
 */
@Composable
fun LoginScreen(
    vm: LoginViewModel,
    gate: BiometricGate,
    onLoggedIn: (mustChange: Boolean) -> Unit,
    onForgotPassword: () -> Unit = {},
) {
    val state by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(state.success) {
        if (state.success) onLoggedIn(state.forcePasswordChange)
    }

    // A saved account tapped while app lock is on: the phone's unlock comes first.
    LaunchedEffect(state.gateFor) {
        val account = state.gateFor ?: return@LaunchedEffect
        vm.onGatePrompted()
        gate.authenticate(subtitle = account.name.ifBlank { account.identifier }) { result ->
            vm.onGateResult(account, result)
        }
    }

    val passwordFocus = remember { FocusRequester() }
    LaunchedEffect(state.focusPassword) {
        if (state.focusPassword > 0) runCatching { passwordFocus.requestFocus() }
    }

    // KIS brand palette (matches the web admin login gradient: deep indigo → khalsa blue).
    val brand = KISTheme.colors
    BoxWithConstraints(
        Modifier
            .fillMaxSize()
            .background(Brush.linearGradient(listOf(brand.loginGradientStart, brand.loginGradientEnd)))
            .safeDrawingPadding()
    ) {
        // Centred when it fits, scrolling when it doesn't (several saved accounts, the keyboard up).
        Column(
            Modifier
                .fillMaxWidth()
                .verticalScroll(rememberScrollState())
                .heightIn(min = maxHeight)
                .padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp, Alignment.CenterVertically),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            if (state.accounts.isNotEmpty()) {
                SavedAccountsCard(
                    accounts = state.accounts,
                    busyIdentifier = state.busyIdentifier.takeIf { state.busy },
                    enabled = !state.busy,
                    onUse = vm::useAccount,
                    onRemove = vm::askRemove,
                )
            }
            PasswordCard(
                state = state,
                hasSavedAccounts = state.accounts.isNotEmpty(),
                passwordFocus = passwordFocus,
                onIdentifier = vm::setIdentifier,
                onPassword = vm::setPassword,
                onSubmit = vm::submit,
                onForgotPassword = onForgotPassword,
            )
        }
    }

    state.confirmRemove?.let { account ->
        val who = account.name.ifBlank { account.identifier }
        AlertDialog(
            onDismissRequest = vm::cancelRemove,
            title = { Text("Remove $who from this phone?") },
            text = { Text("$who will need the password to sign in on this phone again.") },
            confirmButton = { TextButton(onClick = vm::confirmRemove) { Text("Remove") } },
            dismissButton = { TextButton(onClick = vm::cancelRemove) { Text("Cancel") } },
        )
    }

    if (state.offerBiometric) {
        AlertDialog(
            // Back or a tap outside answers "Not now": the popup isn't shown again for this account.
            onDismissRequest = { vm.answerBiometricOffer(false) },
            icon = { Icon(KisIcons.AppLock, contentDescription = null) },
            title = { Text("Sign in faster next time?") },
            text = {
                Text(
                    "Use your fingerprint, face or phone PIN to open KIS School Portal. " +
                        "You won't need your password for 30 days."
                )
            },
            confirmButton = { TextButton(onClick = { vm.answerBiometricOffer(true) }) { Text("Enable") } },
            dismissButton = { TextButton(onClick = { vm.answerBiometricOffer(false) }) { Text("Not now") } },
        )
    }
}

@Composable
private fun SavedAccountsCard(
    accounts: List<SavedAccount>,
    /** The account being opened (its session is refreshing). */
    busyIdentifier: String?,
    enabled: Boolean,
    onUse: (SavedAccount) -> Unit,
    onRemove: (SavedAccount) -> Unit,
) {
    Card(
        modifier = Modifier.widthIn(max = 480.dp).fillMaxWidth().wrapContentHeight(),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
    ) {
        Column(Modifier.padding(vertical = 12.dp)) {
            Text(
                "Saved on this phone",
                style = MaterialTheme.typography.titleSmall,
                fontWeight = FontWeight.SemiBold,
                modifier = Modifier.padding(horizontal = 20.dp, vertical = 6.dp),
            )
            accounts.forEachIndexed { i, account ->
                if (i > 0) HorizontalDivider(Modifier.padding(start = 72.dp, end = 16.dp))
                SavedAccountRow(
                    account = account,
                    busy = busyIdentifier == account.identifier,
                    enabled = enabled,
                    onClick = { onUse(account) },
                    onRemove = { onRemove(account) },
                )
            }
        }
    }
}

@Composable
private fun SavedAccountRow(
    account: SavedAccount,
    busy: Boolean,
    enabled: Boolean,
    onClick: () -> Unit,
    onRemove: () -> Unit,
) {
    val name = account.name.ifBlank { account.identifier }
    val needsPassword = account.needsPassword
    val primary = MaterialTheme.colorScheme.primary
    Row(
        Modifier
            .fillMaxWidth()
            .clickable(
                enabled = enabled,
                onClickLabel = if (needsPassword) "Enter the password for $name" else "Sign in as $name",
                onClick = onClick,
            )
            .padding(start = 16.dp, end = 4.dp, top = 8.dp, bottom = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        ModuleIconCircle(icon = KisIcons.Account, fg = primary, container = primary.copy(alpha = 0.12f), size = 40.dp)
        Spacer(Modifier.width(12.dp))
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(
                    name,
                    style = MaterialTheme.typography.bodyLarge,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                    modifier = Modifier.weight(1f, fill = false),
                )
                roleLabel(account.role)?.let { RoleChip(it) }
            }
            if (account.identifier != name) {
                Text(
                    account.identifier,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
            }
            if (needsPassword) NeedsPasswordTag()
        }
        if (busy) {
            CircularProgressIndicator(Modifier.padding(14.dp).size(20.dp), strokeWidth = 2.dp)
        } else {
            IconButton(onClick = onRemove, enabled = enabled) {
                Icon(KisIcons.Remove, contentDescription = "Remove $name from this phone")
            }
        }
    }
}

@Composable
private fun NeedsPasswordTag() {
    val c = MaterialTheme.colorScheme
    Text(
        "Needs password",
        style = MaterialTheme.typography.labelSmall,
        fontWeight = FontWeight.SemiBold,
        color = c.onErrorContainer,
        maxLines = 1,
        modifier = Modifier
            .background(c.errorContainer, RoundedCornerShape(50))
            .padding(horizontal = 8.dp, vertical = 2.dp),
    )
}

/** Why the person is here ("your sign-in on this phone has expired"): information, not an error. */
@Composable
private fun NoticeBanner(message: String?) {
    if (message.isNullOrBlank()) return
    val c = MaterialTheme.colorScheme
    Text(
        message,
        color = c.onSecondaryContainer,
        style = MaterialTheme.typography.bodyMedium,
        modifier = Modifier
            .fillMaxWidth()
            .background(c.secondaryContainer, RoundedCornerShape(8.dp))
            .padding(12.dp),
    )
}

@Composable
private fun PasswordCard(
    state: LoginUiState,
    hasSavedAccounts: Boolean,
    passwordFocus: FocusRequester,
    onIdentifier: (String) -> Unit,
    onPassword: (String) -> Unit,
    onSubmit: () -> Unit,
    onForgotPassword: () -> Unit,
) {
    val brand = KISTheme.colors
    // The password form's own spinner; a saved account being opened shows its spinner in its row.
    val signingIn = state.busy && state.busyIdentifier == null
    Card(
        modifier = Modifier.widthIn(max = 480.dp).fillMaxWidth().wrapContentHeight(),
        elevation = CardDefaults.cardElevation(defaultElevation = 6.dp)
    ) {
        Column(
            Modifier.padding(24.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            // The crest is 5:4, so only its height is fixed (CLAUDE.md Gotcha #11).
            Image(
                painter = painterResource(R.drawable.crest_mark),
                contentDescription = null,
                contentScale = ContentScale.Fit,
                modifier = Modifier.height(64.dp)
            )
            Text(
                "Khalsa International",
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = brand.schoolName,
                textAlign = TextAlign.Center
            )
            Text(
                "SENIOR SECONDARY SCHOOL",
                style = MaterialTheme.typography.labelMedium,
                color = brand.schoolTagline,
                letterSpacing = 2.sp,
                textAlign = TextAlign.Center
            )
            Text(
                if (hasSavedAccounts) "Sign in with a password" else "Sign in",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )

            NoticeBanner(state.notice)

            OutlinedTextField(
                value = state.identifier,
                onValueChange = onIdentifier,
                label = { Text("Email or phone") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Email, imeAction = ImeAction.Next),
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth()
            )

            OutlinedTextField(
                value = state.password,
                onValueChange = onPassword,
                label = { Text("Password") },
                singleLine = true,
                visualTransformation = PasswordVisualTransformation(),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password, imeAction = ImeAction.Done),
                keyboardActions = KeyboardActions(onDone = { onSubmit() }),
                enabled = !state.busy,
                modifier = Modifier
                    .fillMaxWidth()
                    .focusRequester(passwordFocus)
            )

            ErrorBanner(state.error)

            Button(
                onClick = onSubmit,
                enabled = !state.busy && state.identifier.isNotBlank() && state.password.isNotBlank(),
                modifier = Modifier.fillMaxWidth().height(52.dp)
            ) {
                if (signingIn) CircularProgressIndicator(
                    strokeWidth = 2.dp,
                    modifier = Modifier.height(20.dp)
                ) else Text("Sign in")
            }

            TextButton(
                onClick = onForgotPassword,
                enabled = !state.busy,
                modifier = Modifier.fillMaxWidth()
            ) {
                Text("Forgot password?")
            }
            Text(
                "v${BuildConfig.VERSION_NAME} · build ${BuildConfig.VERSION_CODE}",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                textAlign = TextAlign.Center
            )
        }
    }
}
