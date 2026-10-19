package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/*
 * Replies the Home dashboard reads. Every constructor parameter has a default so Kotlin
 * emits a no-arg constructor: Gson builds the object through it and a key the server
 * leaves out keeps its default (see ResultsDto.kt). DashboardRepository still checks the
 * lists and names for an explicit JSON null before the screens draw them.
 */

// ── GET /attendance/class-summary?from=&to= (backend/app/schemas/attendance.py) ──

/**
 * One class over the date range. Counts cover non-holiday days only; a class nobody
 * marked has zeros and a null [percent].
 */
data class ClassAttendanceRowDto(
    @SerializedName("class_name") val className: String = "",
    /** Students not archived (pending-delete students still count). */
    @SerializedName("class_size") val classSize: Int = 0,
    /** Distinct non-holiday dates with attendance saved (a day saved with no rows counts). */
    @SerializedName("marked_days") val markedDays: Int = 0,
    /** Days saved as a holiday. */
    @SerializedName("holiday_days") val holidayDays: Int = 0,
    val present: Int = 0,
    val absent: Int = 0,
    val leave: Int = 0,
    @SerializedName("half_day") val halfDay: Int = 0,
    /** present + absent + leave + half_day. */
    val records: Int = 0,
    /** (present + 0.5 × half_day) / records × 100, one decimal; null with no records. */
    val percent: Double? = null,
)

data class ClassAttendanceTotalsDto(
    @SerializedName("class_size") val classSize: Int = 0,
    val present: Int = 0,
    val absent: Int = 0,
    val leave: Int = 0,
    @SerializedName("half_day") val halfDay: Int = 0,
    val records: Int = 0,
    val percent: Double? = null,
    /** Classes with at least one marked day in the range. */
    @SerializedName("classes_marked") val classesMarked: Int = 0,
    /** Classes in the caller's scope. */
    @SerializedName("classes_total") val classesTotal: Int = 0,
)

data class ClassAttendanceSummaryDto(
    /** The range actually used (ISO dates); "to" is never later than the server's today. */
    val from: String = "",
    val to: String = "",
    /** Every class in scope, marked or not, in school order. */
    val classes: List<ClassAttendanceRowDto> = emptyList(),
    val totals: ClassAttendanceTotalsDto = ClassAttendanceTotalsDto(),
)

// ── GET /marks/batches/summary?session=[&class=] (backend/app/schemas/marks_batch.py) ──

/** One exam component of a class subject in the session, with its batch's state. */
data class BatchSummaryItemDto(
    @SerializedName("class_name") val className: String = "",
    val subject: String = "",
    /** The exam component's name ("P.T. First", "Semester Second — Practical"). */
    @SerializedName("exam_type") val examType: String = "",
    /** 1 | 2, or null when the component counts in both terms. */
    val term: Int? = null,
    /** "draft" | "submitted", or "none" when no marks are saved for the exam yet. */
    val status: String = "none",
    /** Students in [classSize] with a mark (or a letter, for a graded exam). */
    val entered: Int = 0,
    /** Active students; for an optional subject, the active students who take it. */
    @SerializedName("class_size") val classSize: Int = 0,
    @SerializedName("updated_at") val updatedAt: String? = null,
    val revision: Int = 0,
    @SerializedName("pending_edit_request") val pendingEditRequest: Boolean = false,
)

data class BatchSummaryTotalsDto(
    val draft: Int = 0,
    val submitted: Int = 0,
    /** Items with status "none". */
    val missing: Int = 0,
)

data class BatchSummaryDto(
    val session: String = "",
    val items: List<BatchSummaryItemDto> = emptyList(),
    val totals: BatchSummaryTotalsDto = BatchSummaryTotalsDto(),
)

// ── GET /fees (admins; backend/app/schemas/fee.py FeeOut) ──

/** One fee receipt. */
data class FeePaymentDto(
    val id: Long = 0,
    @SerializedName("student_id") val studentId: Long = 0,
    @SerializedName("student_name") val studentName: String = "",
    @SerializedName("class_name") val className: String = "",
    /** The fee period paid for ("April"), not the day it was paid. */
    val month: String = "",
    val year: String = "",
    /** A Decimal, sent as a JSON string ("1500.00"); Gson reads a bare number into a String too. */
    val amount: String = "0",
    /** The day it was paid (ISO date). */
    val date: String = "",
    @SerializedName("receipt_no") val receiptNo: String = "",
    @SerializedName("created_at") val createdAt: String? = null,
)

// ── GET /staff (admins; backend/app/schemas/staff.py StaffOut, the fields the dashboard reads) ──

data class StaffSummaryDto(
    val id: Long = 0,
    val name: String = "",
    val designation: String = "",
    /** "active" | "pending_delete" | "deleted" (deleted rows are only listed on request). */
    val status: String = "active",
)
