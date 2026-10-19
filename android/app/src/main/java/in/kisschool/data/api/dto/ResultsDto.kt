package `in`.kisschool.data.api.dto

import com.google.gson.annotations.SerializedName

/*
 * GET /marks/results?class=&session=&scope= — the class results table
 * (backend/app/schemas/results.py, ClassResultsOut).
 *
 * Every constructor parameter has a default on purpose: Kotlin then emits a
 * no-arg constructor, Gson builds the object through it, and any key an older
 * server leaves out keeps the default here. (A class with a required parameter
 * is built without running the constructor, so a missing key would be left null
 * even for a non-null Kotlin type.) Session-18 servers send only the v1 fields:
 * names, totals, percentage, grade and status. Numbers are floats on the wire, so
 * marks and totals are Doubles; anything the API can send as null is nullable.
 */

/** One exam component of a subject in the selected scope (column metadata). */
data class ComponentInfoDto(
    @SerializedName("component_name") val componentName: String = "",
    /** Exam group: the part before " — " ("Semester First — Written" → "Semester First"). */
    val group: String = "",
    /** 1 | 2, or null when the component counts in both terms. */
    val term: Int? = null,
    val max: Double = 0.0,
)

/** One subject column of the table. */
data class SubjectColumnDto(
    @SerializedName("subject_name") val subjectName: String = "",
    @SerializedName("subject_name_pa") val subjectNamePa: String? = null,
    val category: String = "",                  // academic | co_curricular | grading
    @SerializedName("order_index") val orderIndex: Int = 0,
    /** Scope max = sum of the in-scope components' max marks; 0 for graded subjects. */
    val max: Double = 0.0,
    @SerializedName("is_grading") val isGrading: Boolean = false,
    /** Worst status over the in-scope batches: submitted | draft | none. */
    @SerializedName("batch_status") val batchStatus: String = "none",
    val components: List<ComponentInfoDto> = emptyList(),
)

/** Per-exam column of the "components" layout (an exam group, or a whole term on Annual). */
data class GroupColumnDto(
    val key: String = "",
    val term: Int? = null,
    @SerializedName("order_index") val orderIndex: Int = 0,
)

/** One student's mark (or letter) for one exam component. */
data class ComponentMarkDto(
    @SerializedName("component_name") val componentName: String = "",
    val group: String = "",
    val term: Int? = null,
    val max: Double = 0.0,
    /** Numeric components; null when not entered. */
    val marks: Double? = null,
    /** Graded components (max 0); null when not entered. */
    @SerializedName("grade_letter") val gradeLetter: String? = null,
    /** draft | submitted, or null when the exam has no batch yet. */
    @SerializedName("batch_status") val batchStatus: String? = null,
    /** True when this mark counts towards the totals. */
    val counted: Boolean = false,
)

/** One per-exam column cell for one subject. */
data class ResultCellDto(
    val key: String = "",
    val obtained: Double = 0.0,
    val max: Double = 0.0,
    val marked: Int = 0,
    val total: Int = 0,
    val status: String = "none",                // complete | partial | missing | none
)

/** One student's result for one subject within the scope. */
data class SubjectResultDto(
    @SerializedName("subject_name") val subjectName: String = "",
    val category: String = "",
    val obtained: Double = 0.0,
    val max: Double = 0.0,
    val percentage: Double? = null,
    /** Null until every in-scope exam of the subject is in (as on the report card); null for graded subjects. */
    val grade: String? = null,
    val status: String = "missing",             // complete | partial | missing
    @SerializedName("is_grading") val isGrading: Boolean = false,
    /** Graded subjects: the letter for this scope (the latest term's on Annual). */
    @SerializedName("grade_letter") val gradeLetter: String? = null,
    /** Graded subjects: {"1": "A2", "2": "B1"} (JSON object keys are strings). */
    @SerializedName("term_letters") val termLetters: Map<String, String> = emptyMap(),
    @SerializedName("batch_status") val batchStatus: String = "none",
    @SerializedName("components_total") val componentsTotal: Int = 0,
    @SerializedName("components_marked") val componentsMarked: Int = 0,
    val components: List<ComponentMarkDto> = emptyList(),
    val cells: List<ResultCellDto> = emptyList(),
)

/** Attendance over the scope's dates (non-holiday days; a half day counts 0.5). */
data class AttendanceSummaryDto(
    @SerializedName("working_days") val workingDays: Int = 0,
    @SerializedName("days_present") val daysPresent: Double = 0.0,
    val pct: Double? = null,
    val counts: Map<String, Int> = emptyMap(),
)

/** One row of the table. */
data class StudentResultDto(
    @SerializedName("student_id") val studentId: Long = 0,
    val name: String = "",
    @SerializedName("roll_no") val rollNo: String? = null,
    val status: String = "active",
    val subjects: List<SubjectResultDto> = emptyList(),
    @SerializedName("total_obtained") val totalObtained: Double = 0.0,
    @SerializedName("total_max") val totalMax: Double = 0.0,
    val percentage: Double? = null,
    /** Null while any subject in the scope is incomplete (as on the report card). */
    val grade: String? = null,
    @SerializedName("has_marks") val hasMarks: Boolean = false,
    /** Competition rank (1, 2, 2, 4) on total marks; null when the student has no marks. */
    val rank: Int? = null,
    @SerializedName("pass_status") val passStatus: String? = null,      // pass | fail | incomplete
    @SerializedName("failed_subjects") val failedSubjects: List<String> = emptyList(),
    /** Annual scope only: Promoted | Conditional | Detained. */
    val promotion: String? = null,
    @SerializedName("draft_components") val draftComponents: Int = 0,
    val attendance: AttendanceSummaryDto? = null,
)

data class SessionDatesDto(
    val start: String = "",
    val end: String = "",
)

/** The whole response. */
data class ClassResultsDto(
    @SerializedName("class_name") val className: String = "",
    val session: String = "",
    val scope: String = "annual",
    @SerializedName("subject_columns") val subjectColumns: List<SubjectColumnDto> = emptyList(),
    val students: List<StudentResultDto> = emptyList(),
    val groups: List<GroupColumnDto> = emptyList(),
    @SerializedName("class_size") val classSize: Int = 0,
    @SerializedName("ranked_count") val rankedCount: Int = 0,
    @SerializedName("include_drafts") val includeDrafts: Boolean = true,
    @SerializedName("has_drafts") val hasDrafts: Boolean = false,
    /** Every subject complete and nothing in draft: the ranks are final. */
    val complete: Boolean = false,
    /** Absent on Session-18 servers, hence the default of 1 (they have no ranks). */
    @SerializedName("engine_version") val engineVersion: Int = 1,
    @SerializedName("session_dates") val sessionDates: SessionDatesDto? = null,
    val warnings: List<String> = emptyList(),
    /**
     * The pass rule pass_status, failed_subjects and promotion were worked out with (the
     * class template's, else the school default). Null on older servers. Anything shown
     * about passing uses these or failed_subjects, never a pass mark of the app's own.
     */
    @SerializedName("pass_pct") val passPct: Double? = null,
    @SerializedName("conditional_max_fails") val conditionalMaxFails: Int? = null,
)
