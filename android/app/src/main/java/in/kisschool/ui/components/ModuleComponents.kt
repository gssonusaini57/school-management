package `in`.kisschool.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.drawBehind
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.isSpecified
import `in`.kisschool.ui.theme.KISTheme
import `in`.kisschool.ui.theme.KisModule

/** Width of the accent rule on a module card's start edge. */
val AccentStripWidth: Dp = 4.dp

/**
 * Draws a [width]-wide rule of [color] down this element's start edge (the right edge in a
 * right-to-left layout), behind its content. Inside a Card it follows the card's rounded
 * corners, because the card clips its content.
 */
fun Modifier.accentStrip(color: Color, width: Dp = AccentStripWidth): Modifier = drawBehind {
    val w = width.toPx()
    val x = if (layoutDirection == LayoutDirection.Ltr) 0f else size.width - w
    drawRect(color, topLeft = Offset(x, 0f), size = Size(w, size.height))
}

/**
 * An icon in a [size] circle: [fg] over [container]. [backing], when given, is an opaque
 * disc drawn first, for a translucent [container] that sits on something other than a
 * card surface (a top app bar).
 */
@Composable
fun ModuleIconCircle(
    icon: ImageVector,
    fg: Color,
    container: Color,
    modifier: Modifier = Modifier,
    size: Dp = 40.dp,
    backing: Color? = null,
    contentDescription: String? = null,
) {
    Box(
        modifier
            .size(size)
            .then(if (backing != null) Modifier.background(backing, CircleShape) else Modifier)
            .background(container, CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Icon(icon, contentDescription = contentDescription, tint = fg, modifier = Modifier.size(size * 0.55f))
    }
}

/** [icon] in [module]'s accent circle: its fg over its container, drawn on the card surface. */
@Composable
fun ModuleIconCircle(
    module: KisModule,
    icon: ImageVector,
    modifier: Modifier = Modifier,
    size: Dp = 40.dp,
    contentDescription: String? = null,
) {
    val accent = KISTheme.colors.module(module)
    ModuleIconCircle(
        icon = icon,
        fg = accent.fg,
        container = accent.container,
        modifier = modifier,
        size = size,
        contentDescription = contentDescription,
    )
}

/** The smallest a top-bar title shrinks to (of the bar's own size) before it ellipsizes. */
private const val MIN_TITLE_SCALE = 0.8f

/**
 * A top app bar title led by the screen's module badge: the module's icon circle on a
 * surface-coloured disc (so the translucent accent reads on the blue bar), then [title].
 * A title too long for the bar (a narrow phone, a large font setting) first shrinks a
 * little, down to [MIN_TITLE_SCALE], and only then ends in "…".
 */
@Composable
fun ModuleTopBarTitle(title: String, module: KisModule, icon: ImageVector) {
    val accent = KISTheme.colors.module(module)
    val base = LocalTextStyle.current
    var scale by remember(title) { mutableFloatStateOf(1f) }
    Row(verticalAlignment = Alignment.CenterVertically) {
        ModuleIconCircle(
            icon = icon,
            fg = accent.fg,
            container = accent.container,
            size = 34.dp,
            backing = MaterialTheme.colorScheme.surface,
        )
        Spacer(Modifier.width(12.dp))
        Text(
            title,
            style = if (base.fontSize.isSpecified) base.copy(fontSize = base.fontSize * scale) else base,
            maxLines = 1,
            softWrap = false,
            overflow = TextOverflow.Ellipsis,
            onTextLayout = { r ->
                val overflowed = r.hasVisualOverflow || (r.lineCount > 0 && r.isLineEllipsized(r.lineCount - 1))
                if (overflowed && scale > MIN_TITLE_SCALE) {
                    scale = (scale - 0.05f).coerceAtLeast(MIN_TITLE_SCALE)
                }
            },
        )
    }
}

/**
 * A dashboard card in [module]'s colours: the accent strip down its start edge, a header row
 * with [icon] in the module's circle, [title] and an optional [subtitle] and [trailing]
 * element (a "View all" link, a count), then [content] below it.
 *
 * Tappable as a whole when [onClick] is given. The card keeps the app's standard Card
 * colours and 2.dp elevation, so it sits with the rest of the app in both themes.
 */
@Composable
fun DashboardCard(
    module: KisModule,
    title: String,
    icon: ImageVector,
    modifier: Modifier = Modifier,
    subtitle: String? = null,
    onClick: (() -> Unit)? = null,
    trailing: (@Composable () -> Unit)? = null,
    content: @Composable ColumnScope.() -> Unit,
) {
    val accent = KISTheme.colors.module(module)
    val elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    val body: @Composable ColumnScope.() -> Unit = {
        Column(
            Modifier
                .fillMaxWidth()
                .accentStrip(accent.strip)
                .padding(start = AccentStripWidth + 16.dp, end = 16.dp, top = 16.dp, bottom = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                ModuleIconCircle(module = module, icon = icon)
                Column(
                    Modifier
                        .weight(1f)
                        .padding(start = 12.dp)
                ) {
                    Text(title, style = MaterialTheme.typography.titleMedium)
                    if (subtitle != null) {
                        Text(
                            subtitle,
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                        )
                    }
                }
                if (trailing != null) trailing()
            }
            content()
        }
    }
    if (onClick != null) {
        Card(onClick = onClick, modifier = modifier.fillMaxWidth(), elevation = elevation, content = body)
    } else {
        Card(modifier = modifier.fillMaxWidth(), elevation = elevation, content = body)
    }
}
