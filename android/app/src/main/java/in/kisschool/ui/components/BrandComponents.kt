package `in`.kisschool.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import `in`.kisschool.ui.theme.KISTheme

/** "Super-admin", "Admin" or "Teacher" for a stored role; null while the role isn't known yet. */
fun roleLabel(role: String?): String? = when (role) {
    null, "" -> null
    "super_admin" -> "Super-admin"
    "admin" -> "Admin"
    else -> "Teacher"
}

/** The brand backdrop: deep indigo at the top to khalsa blue at the bottom (the login gradient's colours). */
@Composable
@ReadOnlyComposable
fun brandGradient(): Brush = Brush.verticalGradient(
    listOf(KISTheme.colors.loginGradientStart, KISTheme.colors.loginGradientEnd)
)

/** The user's role as a small royal-gold-on-deep-indigo pill, for the brand headers. */
@Composable
fun RoleChip(label: String, modifier: Modifier = Modifier) {
    val brand = KISTheme.colors
    val shape = RoundedCornerShape(50)
    Text(
        label,
        color = brand.royalGold,
        style = MaterialTheme.typography.labelMedium,
        fontWeight = FontWeight.SemiBold,
        letterSpacing = 0.4.sp,
        maxLines = 1,
        modifier = modifier
            .background(brand.deepIndigo, shape)
            .border(1.dp, brand.royalGold.copy(alpha = 0.55f), shape)
            .padding(horizontal = 10.dp, vertical = 3.dp),
    )
}

/** The 3.dp royal-gold rule along the bottom of a brand header. */
@Composable
fun BrandRule(modifier: Modifier = Modifier) {
    Box(
        modifier
            .fillMaxWidth()
            .height(3.dp)
            .background(KISTheme.colors.royalGold)
    )
}
