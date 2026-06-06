package `in`.kisschool.ui.screens.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.RowScope
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.YearMonth
import java.time.format.TextStyle
import java.util.Locale

private val MarkedColor = Color(0xFF16A34A)
private val MissedColor = Color(0xFFD97706)
private val HolidayColor = Color(0xFF2563EB)

private enum class DayKind { MARKED, MISSED, HOLIDAY, OFF, FUTURE }

/**
 * Month grid showing attendance coverage for a class. Pure Compose (≤42 fixed
 * cells, no LazyGrid — safe inside a parent verticalScroll). All date math uses
 * java.time.LocalDate (timezone-naive ISO), matching what the backend stores.
 */
@Composable
fun MonthCalendar(
    month: YearMonth,
    markedDates: Set<String>,
    holidays: Set<String>,
    today: LocalDate,
    onPrevMonth: () -> Unit,
    onNextMonth: () -> Unit,
    onDayClick: (iso: String) -> Unit,
    modifier: Modifier = Modifier,
) {
    Column(modifier.fillMaxWidth()) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            IconButton(onClick = onPrevMonth) {
                Icon(Icons.Default.ChevronLeft, contentDescription = "Previous month")
            }
            Text(
                "${month.month.getDisplayName(TextStyle.FULL, Locale.getDefault())} ${month.year}",
                style = MaterialTheme.typography.titleMedium,
                textAlign = TextAlign.Center,
                modifier = Modifier.weight(1f),
            )
            IconButton(onClick = onNextMonth) {
                Icon(Icons.Default.ChevronRight, contentDescription = "Next month")
            }
        }

        Row(Modifier.fillMaxWidth()) {
            listOf("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun").forEach {
                Text(
                    it,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.weight(1f),
                )
            }
        }

        val len = month.lengthOfMonth()
        // Monday-first: DayOfWeek.value is 1=Mon … 7=Sun.
        val offset = month.atDay(1).dayOfWeek.value - DayOfWeek.MONDAY.value
        val totalCells = offset + len
        val rows = (totalCells + 6) / 7

        for (r in 0 until rows) {
            Row(Modifier.fillMaxWidth()) {
                for (c in 0 until 7) {
                    val dayNum = r * 7 + c - offset + 1
                    if (dayNum in 1..len) {
                        val d = month.atDay(dayNum)
                        val iso = d.toString()
                        val kind = when {
                            d.isAfter(today) -> DayKind.FUTURE
                            iso in markedDates -> DayKind.MARKED
                            iso in holidays -> DayKind.HOLIDAY
                            d.dayOfWeek !in WORKING_WEEK.workingDays -> DayKind.OFF
                            else -> DayKind.MISSED
                        }
                        DayCell(
                            day = dayNum,
                            kind = kind,
                            isToday = d == today,
                            onClick = { if (kind != DayKind.FUTURE) onDayClick(iso) },
                        )
                    } else {
                        Box(Modifier.weight(1f).aspectRatio(1f))
                    }
                }
            }
        }

        Row(
            Modifier.fillMaxWidth().padding(top = 8.dp),
            horizontalArrangement = Arrangement.spacedBy(14.dp),
        ) {
            LegendDot(MarkedColor, "Marked")
            LegendDot(MissedColor, "Missed")
            LegendDot(HolidayColor, "Holiday")
            LegendDot(MaterialTheme.colorScheme.surfaceVariant, "Off / future")
        }

        val workingUpToToday = (1..len).count { n ->
            val d = month.atDay(n)
            !d.isAfter(today) && d.dayOfWeek in WORKING_WEEK.workingDays && d.toString() !in holidays
        }
        val markedUpToToday = (1..len).count { n ->
            val d = month.atDay(n)
            !d.isAfter(today) && d.toString() in markedDates
        }
        Text(
            "Marked $markedUpToToday / $workingUpToToday working days this month",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(top = 6.dp),
        )
    }
}

@Composable
private fun RowScope.DayCell(
    day: Int,
    kind: DayKind,
    isToday: Boolean,
    onClick: () -> Unit,
) {
    val bg = when (kind) {
        DayKind.MARKED -> MarkedColor
        DayKind.MISSED -> MissedColor
        DayKind.HOLIDAY -> HolidayColor
        DayKind.OFF -> MaterialTheme.colorScheme.surfaceVariant
        DayKind.FUTURE -> MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f)
    }
    val fg = when (kind) {
        DayKind.MARKED, DayKind.MISSED, DayKind.HOLIDAY -> Color.White
        else -> MaterialTheme.colorScheme.onSurfaceVariant
    }
    Box(
        Modifier
            .weight(1f)
            .aspectRatio(1f)
            .padding(3.dp)
            .clip(RoundedCornerShape(8.dp))
            .background(bg)
            .then(
                if (isToday) Modifier.border(2.dp, MaterialTheme.colorScheme.primary, RoundedCornerShape(8.dp))
                else Modifier
            )
            .clickable(enabled = kind != DayKind.FUTURE, onClick = onClick),
        contentAlignment = Alignment.Center,
    ) {
        Text(
            day.toString(),
            color = fg,
            style = MaterialTheme.typography.labelLarge,
            fontWeight = if (isToday) FontWeight.Bold else FontWeight.Normal,
        )
    }
}

@Composable
private fun LegendDot(color: Color, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(12.dp).clip(CircleShape).background(color))
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            modifier = Modifier.padding(start = 4.dp),
        )
    }
}
