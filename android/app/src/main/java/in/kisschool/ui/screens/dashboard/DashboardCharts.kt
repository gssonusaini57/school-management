package `in`.kisschool.ui.screens.dashboard

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.KeyboardArrowRight
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.Immutable
import androidx.compose.runtime.ReadOnlyComposable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.isSpecified
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import kotlin.math.PI
import kotlin.math.ceil
import kotlin.math.min
import kotlin.math.sqrt

/*
 * The dashboard's chart pieces. Marks carry the status colours; every label and value is
 * in the text colours (onSurface / onSurfaceVariant), so a colour is never the only way
 * to read a number: each ring has a legend with its counts, each bar a written label, and
 * each piece a TalkBack description.
 */

/** A neutral track one step off the card surface, in either theme (empty rings, bar tracks). */
@Composable
@ReadOnlyComposable
fun trackColor(): Color = MaterialTheme.colorScheme.onSurface.copy(alpha = 0.10f)

/** One part of a [RingChart] or [StackedBar]. */
@Immutable
data class ChartPart(val value: Int, val color: Color)

/** The surface-coloured gap between two parts of a ring or a stacked bar. */
private val PartGap = 2.dp

/**
 * A ring of [parts], clockwise from 12 o'clock, with [centerValue] over [centerLabel] in
 * the hole; an empty ring (nothing to show) is a plain track.
 *
 * With [onPartClick], a tap on the ring (or just beside it) reports the part under it,
 * found by the tap's angle ([clockAngle], [ringPartAt]). That is a shortcut for sighted
 * users only: the same actions must also be on buttons (the legend), since TalkBack reads
 * the ring as one image, [description].
 */
@Composable
fun RingChart(
    parts: List<ChartPart>,
    centerValue: String,
    centerLabel: String,
    description: String,
    modifier: Modifier = Modifier,
    ringSize: Dp = 128.dp,
    thickness: Dp = 16.dp,
    onPartClick: ((index: Int) -> Unit)? = null,
) {
    val track = trackColor()
    val click by rememberUpdatedState(onPartClick)
    val values = parts.map { it.value }
    val tappable = if (onPartClick == null) Modifier else Modifier.pointerInput(values, thickness) {
        detectTapGestures { pos ->
            val w = size.width.toFloat()
            val h = size.height.toFloat()
            val outer = min(w, h) / 2f
            val inner = outer - thickness.toPx()
            val slack = 12.dp.toPx()
            val dx = pos.x - w / 2f
            val dy = pos.y - h / 2f
            val r = sqrt(dx * dx + dy * dy)
            if (r < inner - slack || r > outer + slack) return@detectTapGestures
            ringPartAt(clockAngle(dx, dy), values)?.let { click?.invoke(it) }
        }
    }
    Box(
        modifier
            .size(ringSize)
            .then(tappable)
            .clearAndSetSemantics { contentDescription = description },
        contentAlignment = Alignment.Center,
    ) {
        Canvas(Modifier.fillMaxSize()) {
            val stroke = thickness.toPx()
            val diameter = size.minDimension - stroke
            val topLeft = Offset((size.width - diameter) / 2f, (size.height - diameter) / 2f)
            val arc = Size(diameter, diameter)
            val style = Stroke(width = stroke, cap = StrokeCap.Butt)
            val total = values.sumOf { it.coerceAtLeast(0) }
            if (total == 0) {
                drawArc(track, 0f, 360f, false, topLeft, arc, style = style)
                return@Canvas
            }
            // A lone full ring has no neighbour to keep apart.
            val gapDeg = if (values.count { it > 0 } > 1) PartGap.toPx() / (PI.toFloat() * diameter) * 360f else 0f
            var start = -90f
            parts.forEach { p ->
                if (p.value <= 0) return@forEach
                val sweep = p.value * 360f / total
                drawArc(
                    color = p.color,
                    startAngle = start + gapDeg / 2f,
                    sweepAngle = (sweep - gapDeg).coerceAtLeast(0.75f),
                    useCenter = false,
                    topLeft = topLeft,
                    size = arc,
                    style = style,
                )
                start += sweep
            }
        }
        Column(
            Modifier.width(ringSize - thickness * 2 - 8.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            FitText(
                centerValue,
                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.SemiBold),
                color = MaterialTheme.colorScheme.onSurface,
            )
            FitText(
                centerLabel,
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/**
 * One line of text that shrinks (down to [minScale] of [style]'s size) rather than wrap or
 * spill out of a fixed width, such as a ring's hole at a large font setting.
 */
@Composable
fun FitText(
    text: String,
    style: TextStyle,
    modifier: Modifier = Modifier,
    color: Color = Color.Unspecified,
    minScale: Float = 0.6f,
) {
    var scale by remember(text, style) { mutableFloatStateOf(1f) }
    Text(
        text,
        modifier = modifier,
        color = color,
        maxLines = 1,
        softWrap = false,
        overflow = TextOverflow.Clip,
        textAlign = TextAlign.Center,
        style = if (style.fontSize.isSpecified) style.copy(fontSize = style.fontSize * scale) else style,
        onTextLayout = { r ->
            if (r.hasVisualOverflow && scale > minScale) scale = (scale - 0.08f).coerceAtLeast(minScale)
        },
    )
}

/**
 * A legend line: [color]'s dot, [label] and [value]. With [onClick] it is a real button
 * (48.dp tall, a chevron, [onClickLabel] for TalkBack's "double-tap to …"), so whatever a
 * tap on the chart does is reachable without a precise tap. TalkBack reads [description].
 */
@Composable
fun LegendRow(
    color: Color,
    label: String,
    value: String,
    description: String,
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    onClickLabel: String? = null,
) {
    Row(
        modifier
            .fillMaxWidth()
            .heightIn(min = if (onClick != null) 48.dp else 32.dp)
            .clip(RoundedCornerShape(8.dp))
            .then(
                if (onClick != null) Modifier.clickable(onClickLabel = onClickLabel, role = Role.Button, onClick = onClick)
                else Modifier
            )
            // After clickable, so the click action stays and only the children's text is replaced.
            .clearAndSetSemantics { contentDescription = description }
            .padding(horizontal = 8.dp, vertical = 4.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(Modifier.size(12.dp).background(color, CircleShape))
        Spacer(Modifier.width(10.dp))
        Text(
            label,
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Text(
            value,
            style = MaterialTheme.typography.bodyMedium,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface,
        )
        if (onClick != null) {
            Icon(
                Icons.AutoMirrored.Filled.KeyboardArrowRight,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.padding(start = 2.dp).size(20.dp),
            )
        }
    }
}

/** A key line for a chart's colours: small dots with their labels, wrapped as needed. */
@OptIn(androidx.compose.foundation.layout.ExperimentalLayoutApi::class)
@Composable
fun ColorKey(entries: List<Pair<Color, String>>, modifier: Modifier = Modifier) {
    androidx.compose.foundation.layout.FlowRow(
        modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.spacedBy(14.dp),
        verticalArrangement = Arrangement.spacedBy(4.dp),
    ) {
        entries.forEach { (color, label) ->
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(Modifier.size(10.dp).background(color, CircleShape))
                Text(
                    label,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(start = 4.dp),
                )
            }
        }
    }
}

/** One KPI tile: an icon in its status colour, the value, and what it counts. */
@Immutable
data class Kpi(
    val icon: ImageVector,
    val tint: Color,
    val label: String,
    val value: String,
    /** What TalkBack reads, e.g. "Absent: 3 students". */
    val description: String,
    val onClick: (() -> Unit)? = null,
    val onClickLabel: String? = null,
)

/**
 * [kpis] as tiles in rows of equal height, as many to a row as fit at [minTileWidth]
 * (then evened out, so 6 tiles make 2 rows of 3 rather than 4 + 2). The tiles sit on the
 * plain surface colour, one step off the card.
 */
@Composable
fun KpiGrid(kpis: List<Kpi>, modifier: Modifier = Modifier, minTileWidth: Dp = 132.dp) {
    if (kpis.isEmpty()) return
    BoxWithConstraints(modifier.fillMaxWidth()) {
        val gap = 8.dp
        val fit = ((maxWidth + gap) / (minTileWidth + gap)).toInt().coerceIn(1, kpis.size)
        val rows = ceil(kpis.size / fit.toFloat()).toInt()
        val columns = ceil(kpis.size / rows.toFloat()).toInt()
        Column(verticalArrangement = Arrangement.spacedBy(gap)) {
            kpis.chunked(columns).forEach { row ->
                Row(
                    Modifier
                        .fillMaxWidth()
                        .height(IntrinsicSize.Min),
                    horizontalArrangement = Arrangement.spacedBy(gap),
                ) {
                    row.forEach { k ->
                        KpiTile(
                            k,
                            Modifier
                                .weight(1f)
                                .fillMaxHeight(),
                        )
                    }
                    repeat(columns - row.size) { Spacer(Modifier.weight(1f)) }
                }
            }
        }
    }
}

@Composable
private fun KpiTile(k: Kpi, modifier: Modifier = Modifier) {
    val onClick = k.onClick
    Column(
        modifier
            .heightIn(min = 72.dp)
            .clip(RoundedCornerShape(12.dp))
            .background(MaterialTheme.colorScheme.surface)
            .then(
                if (onClick != null) Modifier.clickable(onClickLabel = k.onClickLabel, role = Role.Button, onClick = onClick)
                else Modifier
            )
            .clearAndSetSemantics { contentDescription = k.description }
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalArrangement = Arrangement.spacedBy(2.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(k.icon, contentDescription = null, tint = k.tint, modifier = Modifier.size(20.dp))
            Spacer(Modifier.weight(1f))
            if (onClick != null) {
                Icon(
                    Icons.AutoMirrored.Filled.KeyboardArrowRight,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.size(18.dp),
                )
            }
        }
        Text(
            k.value,
            style = MaterialTheme.typography.titleLarge,
            fontWeight = FontWeight.SemiBold,
            color = MaterialTheme.colorScheme.onSurface,
            maxLines = 1,
        )
        Text(
            k.label,
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** A horizontal meter: [percent] (0..100) of the track filled in [color]; null fills nothing. */
@Composable
fun PercentBar(percent: Double?, color: Color, modifier: Modifier = Modifier, height: Dp = 8.dp) {
    val fill = ((percent ?: 0.0) / 100.0).coerceIn(0.0, 1.0).toFloat()
    Box(
        modifier
            .fillMaxWidth()
            .height(height)
            .clip(RoundedCornerShape(height / 2))
            .background(trackColor())
    ) {
        if (fill > 0f) {
            Box(
                Modifier
                    .fillMaxWidth(fill)
                    .fillMaxHeight()
                    .clip(RoundedCornerShape(height / 2))
                    .background(color)
            )
        }
    }
}

/** [parts] side by side in proportion, 2.dp of card surface between them; all zero is a bare track. */
@Composable
fun StackedBar(parts: List<ChartPart>, modifier: Modifier = Modifier, height: Dp = 8.dp) {
    val shown = parts.filter { it.value > 0 }
    Row(
        modifier
            .fillMaxWidth()
            .height(height)
            .clip(RoundedCornerShape(height / 2)),
        horizontalArrangement = Arrangement.spacedBy(PartGap),
    ) {
        if (shown.isEmpty()) {
            Box(Modifier.fillMaxSize().background(trackColor()))
        } else {
            shown.forEach { p ->
                Box(
                    Modifier
                        .weight(p.value.toFloat())
                        .fillMaxHeight()
                        .background(p.color)
                )
            }
        }
    }
}

/**
 * A card's body for its [load]: a spinner on the first load, the error and "Try again"
 * when it failed with nothing to show, else [content], dimmed while a reload runs (no
 * jump back to a spinner) with any reload error above it.
 */
@Composable
fun <T> CardContent(load: Loadable<T>, onRetry: () -> Unit, content: @Composable ColumnScope.(T) -> Unit) {
    val data = load.data
    val error = load.error
    when {
        data != null -> {
            if (error != null) ErrorWithRetry(error, onRetry)
            Column(
                Modifier
                    .fillMaxWidth()
                    .alpha(if (load.loading) 0.55f else 1f),
                verticalArrangement = Arrangement.spacedBy(12.dp),
            ) { content(data) }
        }
        error != null -> ErrorWithRetry(error, onRetry)
        else -> LoadingRow()
    }
}

@Composable
private fun ErrorWithRetry(message: String, onRetry: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        ErrorBanner(message)
        TextButton(onClick = onRetry) { Text("Try again") }
    }
}

/**
 * What stands in for a card the server is too old for: one line, "[title]: [message]",
 * so the rest of the dashboard still reads in order.
 */
@Composable
fun UnavailableNote(title: String, message: String, modifier: Modifier = Modifier) {
    Row(
        modifier
            .fillMaxWidth()
            .padding(horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(
            Icons.Outlined.Info,
            contentDescription = null,
            tint = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.size(16.dp),
        )
        Spacer(Modifier.width(8.dp))
        Text(
            "$title: $message",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
        )
    }
}

/** A small filled dot, e.g. beside "Edit request" (always with its words, never alone). */
@Composable
fun Dot(color: Color, modifier: Modifier = Modifier, size: Dp = 8.dp) {
    Box(modifier.size(size).background(color, CircleShape))
}
