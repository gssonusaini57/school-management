package `in`.kisschool.ui.screens.results

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.PictureAsPdf
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.material3.VerticalDivider
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import `in`.kisschool.data.api.dto.ClassResultsDto
import `in`.kisschool.data.api.dto.SubjectColumnDto
import `in`.kisschool.data.api.dto.SubjectResultDto
import `in`.kisschool.data.api.dto.StudentResultDto
import `in`.kisschool.ui.components.ClassDropdown
import `in`.kisschool.ui.components.EmptyState
import `in`.kisschool.ui.components.ErrorBanner
import `in`.kisschool.ui.components.LoadingRow
import kotlin.math.abs
import kotlin.math.roundToLong

private val Amber = Color(0xFFD97706)

private val ROLL_W = 40.dp
private val NAME_W = 132.dp
private val SUBJ_W = 68.dp
private val TOTAL_W = 84.dp
private val PCT_W = 60.dp
private val GRADE_W = 52.dp
private val RANK_W = 52.dp
private val HEADER_H = 70.dp
private val ROW_H = 44.dp

/** 45.0 → "45", 45.25 → "45.3"; locale-independent so digits never change with the phone's language. */
internal fun fmtNum(v: Double): String {
    if (v.isNaN() || v.isInfinite()) return "—"
    val tenths = (v * 10).roundToLong()
    val sign = if (tenths < 0) "-" else ""
    val a = abs(tenths)
    return if (a % 10 == 0L) "$sign${a / 10}" else "$sign${a / 10}.${a % 10}"
}

/** A graded subject (letters, no marks). v1 servers don't send is_grading, but its max is 0. */
private fun SubjectColumnDto.graded(): Boolean = isGrading || max <= 0.0

/** True when the student has a numeric mark in the scope (totals, % and grade mean something). */
private fun StudentResultDto.hasNumericMarks(): Boolean =
    hasMarks || subjects.any { it.max > 0.0 && it.status != "missing" }

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ResultsScreen(
    vm: ResultsViewModel,
    onBack: () -> Unit,
    onOpenReportCard: (studentId: Long, name: String) -> Unit,
) {
    val s by vm.state.collectAsStateWithLifecycle()

    LaunchedEffect(s.openCard) {
        val card = s.openCard ?: return@LaunchedEffect
        vm.consumeOpenCard()
        onOpenReportCard(card.studentId, card.name)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Results & report cards") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
                    }
                },
                actions = {
                    IconButton(onClick = vm::reload, enabled = s.cls != null && !s.loading) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.primary,
                    titleContentColor = MaterialTheme.colorScheme.onPrimary,
                    navigationIconContentColor = MaterialTheme.colorScheme.onPrimary,
                    actionIconContentColor = MaterialTheme.colorScheme.onPrimary,
                ),
            )
        }
    ) { padding ->
        Column(
            Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                ClassDropdown(
                    classes = s.classOptions,
                    selected = s.cls,
                    onSelect = vm::selectClass,
                    label = "Class",
                    modifier = Modifier.weight(1f),
                )
                ClassDropdown(
                    classes = s.sessionOptions.ifEmpty { listOf(s.session) },
                    selected = s.session,
                    onSelect = vm::selectSession,
                    label = "Session",
                    modifier = Modifier.weight(1f),
                )
            }
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                ResultScope.entries.forEach { sc ->
                    FilterChip(
                        selected = s.scope == sc,
                        onClick = { vm.selectScope(sc) },
                        label = { Text(sc.label) },
                    )
                }
            }
            s.scopeNote?.let { NoteText(it) }

            val r = s.results
            when {
                s.cls == null -> EmptyState("No classes assigned yet.")
                s.loading -> LoadingRow()
                s.error != null -> {
                    ErrorBanner(s.error)
                    OutlinedButton(onClick = vm::reload) { Text("Try again") }
                }
                r == null -> EmptyState("Pick a class to see its results.")
                r.subjectColumns.isEmpty() ->
                    EmptyState("No subjects are set up for ${r.className.ifBlank { s.cls.orEmpty() }} yet.")
                r.students.isEmpty() -> EmptyState("No students in this class.")
                r.students.none { it.hasAnyMarks() } ->
                    EmptyState("No marks entered for ${s.scope.label} ${s.session} yet.")
                else -> ResultsContent(r = r, scope = s.scope, onRowClick = vm::openStudent)
            }
        }
    }

    val student = s.selectedStudent
    val results = s.results
    if (student != null && results != null) {
        val sheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)
        ModalBottomSheet(onDismissRequest = vm::closeStudent, sheetState = sheetState) {
            StudentSheet(
                st = student,
                r = results,
                scope = s.scope,
                template = s.cardTemplate,
                busyThis = s.cardBusyFor == student.studentId,
                busyOther = s.cardBusyName.takeIf { s.cardBusyFor != null && s.cardBusyFor != student.studentId },
                error = s.cardError?.takeIf { it.studentId == student.studentId }?.message,
                onReportCard = { vm.makeReportCard(student.studentId) },
            )
        }
    }
}

@Composable
private fun ResultsContent(r: ClassResultsDto, scope: ResultScope, onRowClick: (Long) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(
            listOf(r.className, scope.label, r.session).filter { it.isNotBlank() }.joinToString(" · "),
            style = MaterialTheme.typography.titleMedium,
        )
        Text(
            buildString {
                append("${r.students.size} students")
                if (r.rankedCount > 0) append(" · ${r.rankedCount} ranked")
                append(" · tap a student for details and the report card")
            },
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (!r.complete && r.students.any { it.rank != null }) {
            NoteText("Ranks provisional: some marks are still missing or in draft.", warn = true)
        }
        r.warnings.filter { it.isNotBlank() }.take(3).forEach { NoteText(it) }
        Legend(showDraft = r.hasDrafts || r.subjectColumns.any { it.batchStatus == "draft" })
        ResultsTable(r, onRowClick)
        if (r.subjectColumns.size > 2) {
            Text(
                "Swipe the table sideways to see every subject.",
                style = MaterialTheme.typography.labelSmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

@Composable
private fun ResultsTable(r: ClassResultsDto, onRowClick: (Long) -> Unit) {
    val outline = MaterialTheme.colorScheme.outlineVariant
    val headerBg = MaterialTheme.colorScheme.surfaceVariant
    val stripe = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.35f)
    val shape = RoundedCornerShape(8.dp)
    fun rowBg(i: Int) = if (i % 2 == 1) stripe else Color.Transparent

    // Every row has a fixed height, so the table's height is known up front. Setting it
    // gives the divider (fillMaxHeight) a bounded height inside the vertical scroll.
    Row(
        Modifier
            .fillMaxWidth()
            .height(HEADER_H + ROW_H * r.students.size)
            .clip(shape)
            .border(1.dp, outline, shape),
    ) {
        // Frozen columns: roll + name stay put while the marks scroll sideways.
        Column(Modifier.width(ROLL_W + NAME_W)) {
            Row(Modifier.height(HEADER_H).fillMaxWidth().background(headerBg), verticalAlignment = Alignment.CenterVertically) {
                HeaderText("Roll", ROLL_W)
                HeaderText("Name", NAME_W, align = TextAlign.Start)
            }
            r.students.forEachIndexed { i, st ->
                Row(
                    Modifier
                        .height(ROW_H)
                        .fillMaxWidth()
                        .background(rowBg(i))
                        .clickable { onRowClick(st.studentId) },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        st.rollNo?.ifBlank { null } ?: "—",
                        modifier = Modifier.width(ROLL_W),
                        textAlign = TextAlign.Center,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    Text(
                        st.name,
                        modifier = Modifier.width(NAME_W).padding(end = 6.dp),
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Medium,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
        VerticalDivider(color = outline)
        Column(Modifier.weight(1f).horizontalScroll(rememberScrollState())) {
            Row(Modifier.height(HEADER_H).background(headerBg)) {
                r.subjectColumns.forEach { SubjectHeader(it) }
                HeaderText("Total", TOTAL_W, Modifier.fillMaxHeight())
                HeaderText("%", PCT_W, Modifier.fillMaxHeight())
                HeaderText("Grade", GRADE_W, Modifier.fillMaxHeight())
                HeaderText("Rank", RANK_W, Modifier.fillMaxHeight())
            }
            r.students.forEachIndexed { i, st ->
                val bySubject = st.subjects.associateBy { it.subjectName }
                val numeric = st.hasNumericMarks()
                Row(
                    Modifier
                        .height(ROW_H)
                        .background(rowBg(i))
                        .clickable { onRowClick(st.studentId) },
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    r.subjectColumns.forEach { col -> SubjectCell(col, bySubject[col.subjectName]) }
                    ValueCell(
                        if (numeric && st.totalMax > 0.0) "${fmtNum(st.totalObtained)}/${fmtNum(st.totalMax)}" else "—",
                        TOTAL_W, bold = true,
                    )
                    ValueCell(st.percentage?.takeIf { numeric }?.let { "${fmtNum(it)}%" } ?: "—", PCT_W)
                    ValueCell(st.grade?.takeIf { numeric && it.isNotBlank() } ?: "—", GRADE_W)
                    ValueCell(st.rank?.toString() ?: "—", RANK_W)
                }
            }
        }
    }
}

@Composable
private fun HeaderText(text: String, width: Dp, modifier: Modifier = Modifier, align: TextAlign = TextAlign.Center) {
    Box(modifier.width(width).padding(horizontal = 4.dp), contentAlignment = Alignment.Center) {
        Text(
            text,
            modifier = Modifier.fillMaxWidth(),
            style = MaterialTheme.typography.labelMedium,
            fontWeight = FontWeight.SemiBold,
            textAlign = align,
        )
    }
}

@Composable
private fun SubjectHeader(col: SubjectColumnDto) {
    Column(
        Modifier.width(SUBJ_W).fillMaxHeight().padding(horizontal = 4.dp, vertical = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Text(
            col.subjectName,
            style = MaterialTheme.typography.labelSmall,
            fontWeight = FontWeight.SemiBold,
            textAlign = TextAlign.Center,
            maxLines = 2,
            overflow = TextOverflow.Ellipsis,
            lineHeight = 13.sp,
        )
        Text(
            if (col.graded()) "grade" else "/${fmtNum(col.max)}",
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (col.batchStatus == "draft") DraftBadge()
    }
}

@Composable
private fun SubjectCell(col: SubjectColumnDto, sub: SubjectResultDto?) {
    Box(Modifier.width(SUBJ_W).fillMaxHeight(), contentAlignment = Alignment.Center) {
        when {
            sub == null || sub.status == "missing" -> Dash()
            col.graded() -> MarkValue(sub.gradeLetter?.ifBlank { null } ?: "—", partial = sub.status == "partial")
            else -> MarkValue(fmtNum(sub.obtained), partial = sub.status == "partial")
        }
    }
}

@Composable
private fun ValueCell(text: String, width: Dp, bold: Boolean = false) {
    Text(
        text,
        modifier = Modifier.width(width).padding(horizontal = 2.dp),
        textAlign = TextAlign.Center,
        style = MaterialTheme.typography.bodySmall,
        fontWeight = if (bold) FontWeight.SemiBold else FontWeight.Normal,
        color = if (text == "—") MaterialTheme.colorScheme.onSurfaceVariant else MaterialTheme.colorScheme.onSurface,
        maxLines = 1,
    )
}

@Composable
private fun MarkValue(text: String, partial: Boolean) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        if (partial) {
            Box(Modifier.size(6.dp).clip(CircleShape).background(Amber))
            Spacer(Modifier.width(3.dp))
        }
        Text(text, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun Dash() {
    Text("—", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
}

@Composable
private fun DraftBadge(modifier: Modifier = Modifier) {
    Text(
        "Draft",
        modifier = modifier
            .border(1.dp, Amber, RoundedCornerShape(4.dp))
            .padding(horizontal = 4.dp),
        color = Amber,
        fontSize = 9.sp,
        lineHeight = 12.sp,
        fontWeight = FontWeight.SemiBold,
    )
}

@Composable
private fun Legend(showDraft: Boolean) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(Modifier.size(6.dp).clip(CircleShape).background(Amber))
        Text(
            buildString {
                append(" some exams missing   — not entered")
                if (showDraft) append("   Draft = not submitted yet")
            },
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
    }
}

@Composable
private fun NoteText(text: String, warn: Boolean = false) {
    Text(
        text,
        style = MaterialTheme.typography.bodySmall,
        color = if (warn) Amber else MaterialTheme.colorScheme.onSurfaceVariant,
    )
}

// ── Student details sheet ───────────────────────────────────────────────

@Composable
private fun StudentSheet(
    st: StudentResultDto,
    r: ClassResultsDto,
    scope: ResultScope,
    template: CardTemplateState,
    busyThis: Boolean,
    /** Name of another student whose card is still being made (one at a time), else null. */
    busyOther: String?,
    error: String?,
    onReportCard: () -> Unit,
) {
    val numeric = st.hasNumericMarks()
    Column(
        Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp)
            .padding(bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(10.dp),
    ) {
        Text(st.name, style = MaterialTheme.typography.titleLarge)
        Text(
            listOfNotNull(
                st.rollNo?.ifBlank { null }?.let { "Roll $it" },
                r.className.ifBlank { null },
                "${scope.label} ${r.session}",
            ).joinToString(" · "),
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
        )

        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            Stat("Total", if (numeric && st.totalMax > 0.0) "${fmtNum(st.totalObtained)}/${fmtNum(st.totalMax)}" else "—", Modifier.weight(1.4f))
            Stat("%", st.percentage?.takeIf { numeric }?.let { "${fmtNum(it)}%" } ?: "—", Modifier.weight(1f))
            Stat("Grade", st.grade?.takeIf { numeric && it.isNotBlank() } ?: "—", Modifier.weight(1f))
            Stat(
                "Rank",
                st.rank?.let { rank -> if (r.classSize > 0) "$rank / ${r.classSize}" else "$rank" } ?: "—",
                Modifier.weight(1f),
            )
        }
        st.attendance?.let { a ->
            val pct = a.pct?.let { "${fmtNum(it)}%" } ?: "—"
            Text(
                "Attendance: $pct · ${fmtNum(a.daysPresent)} of ${a.workingDays} days",
                style = MaterialTheme.typography.bodyMedium,
            )
        }
        resultLine(st)?.let { line ->
            Text(line, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }

        ReportCardSection(template, busyThis, busyOther, error, onReportCard)

        HorizontalDivider(Modifier.padding(vertical = 4.dp))
        Text("Marks by exam", style = MaterialTheme.typography.titleSmall)
        val bySubject = st.subjects.associateBy { it.subjectName }
        r.subjectColumns.forEach { col -> SubjectBlock(col, bySubject[col.subjectName]) }
    }
}

/** "Result: Pass", "Failed: Maths, Science", the annual promotion … or null when not known. */
private fun resultLine(st: StudentResultDto): String? {
    val parts = mutableListOf<String>()
    when (st.passStatus) {
        "pass" -> parts += "Result: Pass"
        "fail" -> parts += "Result: Fail" + st.failedSubjects.takeIf { it.isNotEmpty() }
            ?.joinToString(", ", prefix = " (", postfix = ")").orEmpty()
        "incomplete" -> parts += "Result: not final yet (marks missing)"
    }
    st.promotion?.ifBlank { null }?.let { parts += it }
    return parts.takeIf { it.isNotEmpty() }?.joinToString(" · ")
}

@Composable
private fun Stat(label: String, value: String, modifier: Modifier) {
    Column(
        modifier
            .clip(RoundedCornerShape(8.dp))
            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.6f))
            .padding(horizontal = 8.dp, vertical = 6.dp),
    ) {
        Text(label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold, maxLines = 1)
    }
}

@Composable
private fun ReportCardSection(
    template: CardTemplateState,
    busyThis: Boolean,
    busyOther: String?,
    error: String?,
    onReportCard: () -> Unit,
) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        when (template) {
            CardTemplateState.Idle, CardTemplateState.Checking -> Row(verticalAlignment = Alignment.CenterVertically) {
                CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.size(18.dp))
                Text(
                    "  Checking for a report-card template…",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
            CardTemplateState.Missing -> {
                ReportCardButton(enabled = false, busy = false, onClick = {})
                NoteText("No report-card template for this class and term yet")
            }
            is CardTemplateState.Unavailable -> {
                ReportCardButton(enabled = false, busy = false, onClick = {})
                NoteText(template.message)
            }
            is CardTemplateState.Ready -> {
                ReportCardButton(enabled = !busyThis && busyOther == null, busy = busyThis, onClick = onReportCard)
                busyOther?.let { NoteText("Preparing ${it.ifBlank { "another student" }}'s card…") }
            }
        }
        ErrorBanner(error)
    }
}

@Composable
private fun ReportCardButton(enabled: Boolean, busy: Boolean, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled, modifier = Modifier.fillMaxWidth()) {
        if (busy) {
            CircularProgressIndicator(
                strokeWidth = 2.dp,
                modifier = Modifier.size(18.dp),
                color = MaterialTheme.colorScheme.onPrimary,
            )
            Text("  Preparing report card…")
        } else {
            Icon(Icons.Default.PictureAsPdf, contentDescription = null)
            Text("  Report card")
        }
    }
}

@Composable
private fun SubjectBlock(col: SubjectColumnDto, sub: SubjectResultDto?) {
    val graded = col.graded()
    Column(Modifier.fillMaxWidth(), verticalArrangement = Arrangement.spacedBy(2.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(
                col.subjectName,
                modifier = Modifier.weight(1f),
                style = MaterialTheme.typography.bodyMedium,
                fontWeight = FontWeight.SemiBold,
            )
            val summary = when {
                sub == null || sub.status == "missing" -> "—"
                graded -> sub.gradeLetter?.ifBlank { null } ?: "—"
                // A subject's grade only once all its exams are in, as on the report card:
                // the marks so far over the whole max would understate it.
                else -> "${fmtNum(sub.obtained)}/${fmtNum(sub.max)}" +
                    (sub.grade?.takeIf { sub.status == "complete" && it.isNotBlank() }?.let { " · $it" } ?: "")
            }
            MarkValue(summary, partial = sub?.status == "partial")
        }
        sub?.components.orEmpty().forEach { c ->
            Row(Modifier.padding(start = 12.dp), verticalAlignment = Alignment.CenterVertically) {
                Text(
                    c.componentName,
                    modifier = Modifier.weight(1f),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
                if (c.batchStatus == "draft") DraftBadge(Modifier.padding(end = 6.dp))
                val value = if (graded || c.max <= 0.0) {
                    c.gradeLetter?.ifBlank { null } ?: "—"
                } else {
                    c.marks?.let { "${fmtNum(it)}/${fmtNum(c.max)}" } ?: "—"
                }
                Text(value, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
