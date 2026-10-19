package `in`.kisschool.ui.lock

import androidx.activity.compose.BackHandler
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentHeight
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import `in`.kisschool.R
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisIcons

/**
 * Full-screen cover shown while the app is locked: the crest on the brand gradient, whose
 * account is signed in, a button to run the unlock prompt again, and the two ways round
 * it — the password, or another saved account. A Surface, so touches never reach the
 * screen underneath.
 */
@Composable
fun LockScreen(
    accountName: String,
    /** Why the last attempt didn't unlock (a lockout, a timeout); null when nothing to say. */
    message: String?,
    /** The prompt is up, or the session is being refreshed after a successful unlock. */
    busy: Boolean,
    onUnlock: () -> Unit,
    onUsePassword: () -> Unit,
    onSwitchAccount: () -> Unit,
    onBack: () -> Unit,
) {
    BackHandler(onBack = onBack)
    val brand = KISTheme.colors
    Surface(Modifier.fillMaxSize(), color = Color.Transparent) {
        Box(
            Modifier
                .fillMaxSize()
                .background(Brush.linearGradient(listOf(brand.loginGradientStart, brand.loginGradientEnd)))
                .padding(24.dp),
            contentAlignment = Alignment.Center,
        ) {
            Card(
                modifier = Modifier.widthIn(max = 480.dp).fillMaxWidth().wrapContentHeight(),
                elevation = CardDefaults.cardElevation(defaultElevation = 6.dp),
            ) {
                Column(
                    Modifier.padding(24.dp),
                    verticalArrangement = Arrangement.spacedBy(14.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    // The crest is 5:4, so only its height is fixed (CLAUDE.md Gotcha #11).
                    Image(
                        painter = painterResource(R.drawable.crest_mark),
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.height(64.dp),
                    )
                    Text(
                        "Khalsa International",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.Bold,
                        color = brand.schoolName,
                        textAlign = TextAlign.Center,
                    )
                    Text(
                        "SENIOR SECONDARY SCHOOL",
                        style = MaterialTheme.typography.labelMedium,
                        color = brand.schoolTagline,
                        letterSpacing = 2.sp,
                        textAlign = TextAlign.Center,
                    )
                    Spacer(Modifier.height(4.dp))
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Icon(
                            KisIcons.AppLock,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.size(22.dp),
                        )
                        Text("Locked", style = MaterialTheme.typography.titleMedium)
                    }
                    if (accountName.isNotBlank()) {
                        Text(
                            "Signed in as ${accountName.trim()}",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            textAlign = TextAlign.Center,
                        )
                    }
                    Text(
                        "Use your fingerprint, face or phone PIN to open KIS School Portal.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        textAlign = TextAlign.Center,
                    )

                    ErrorBanner(message)

                    Button(
                        onClick = onUnlock,
                        enabled = !busy,
                        modifier = Modifier.fillMaxWidth().height(52.dp),
                    ) {
                        if (busy) CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.size(20.dp))
                        else Text("Unlock")
                    }
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceEvenly,
                    ) {
                        TextButton(onClick = onUsePassword, enabled = !busy) { Text("Use password") }
                        TextButton(onClick = onSwitchAccount, enabled = !busy) { Text("Switch account") }
                    }
                }
            }
        }
    }
}
