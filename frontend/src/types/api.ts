export type Role = "admin" | "super_admin" | "staff";

export type RecordStatus = "active" | "pending_delete" | "deleted";

export interface SoftDeleteFields {
  status: RecordStatus;
  delete_requested_at: string | null;
  delete_requested_by: string | null;
  delete_reason: string | null;
  deleted_at: string | null;
  deleted_by: string | null;
}

export interface LoginResponse {
  token: string;
  role: Role;
  name: string;
  allowed_classes: string[];
  allowed_menus?: string[];
  force_password_change?: boolean;
}

export interface Student extends SoftDeleteFields {
  id: number;
  name: string;
  father: string;
  mother: string;
  dob: string | null;
  gender: string;
  village: string;
  phone: string;
  aadhar: string;
  alt_phone: string;
  religion: string;
  prev_school: string;
  bank_name: string;
  bank_acc: string;
  bank_ifsc: string;
  annual_fee: string | number;
  class_name: string;
  admission_no: number | null;
  admission_id: string | null;
  roll_no: string | null;
  created_at: string;
  added_by: string;
  updated_at: string;
  updated_by: string;
  has_photo: boolean;
  has_dob_cert: boolean;
  has_aadhar: boolean;
  // Edit-approval workflow:
  // - `has_pending_edit` is set on BOTH list + single-row reads (used by the
  //   Students table to hide the pencil + show a badge).
  // - The other three are only populated on single-row GET /students/:id.
  has_pending_edit?: boolean;
  pending_edit_request_id?: number | null;
  pending_edit_requested_by?: string | null;
  pending_edit_requested_at?: string | null;
}

export interface StudentEditDiffEntry {
  old: unknown;
  new: unknown;
}
export type StudentEditDiff = Record<string, StudentEditDiffEntry>;

export interface EditRequestItem {
  id: number;
  student_id: number;
  student_name: string;
  class_name: string | null;
  requested_at: string;
  requested_by: string;
  requested_by_role: "admin" | "staff";
  changes: StudentEditDiff;
  status: "pending" | "approved" | "rejected";
  reviewed_at: string | null;
  reviewed_by: string | null;
  reject_reason: string | null;
}

export interface StudentPage {
  items: Student[];
  total: number;
  page: number;
  page_size: number;
}

export type DocumentKind = "photo" | "dob_cert" | "aadhar";

export interface AttendanceRecord {
  class_name: string;
  date: string;
  records: Record<number, "P" | "A" | "L">;
}

export interface AttendanceSummary {
  date: string;
  total: number;
  present: number;
  absent: number;
  leave: number;
  percent: number;
}

export interface Mark {
  id: number;
  student_id: number;
  class_name: string;
  exam_type: string;
  subject: string;
  marks: number;
  max_marks: number;
  session: string;
  created_at: string;
}

export interface FeePayment {
  id: number;
  student_id: number;
  student_name: string;
  class_name: string;
  month: string;
  year: string;
  amount: string | number;
  date: string;
  receipt_no: string;
  created_at: string;
}

export interface Notice {
  id: number;
  title: string;
  content: string;
  priority: "normal" | "medium" | "high";
  audience: string;
  posted_by: string;
  created_at: string;
}

export interface Staff extends SoftDeleteFields {
  id: number;
  name: string;
  designation: string;
  phone: string;
  email: string;
  employee_id: string;
  assigned_classes: string[];
  allowed_menus: string[];
  force_password_change: boolean;
  has_temp_password?: boolean;
  temp_password_set_at?: string | null;
  temp_password_set_by?: string | null;
  created_at: string;
}

export interface StaffCreateResponse extends Staff {
  initial_password: string;
}

export interface StaffUpdateResponse extends Staff {
  new_password?: string | null;
}

export interface DeletionRequestItem {
  kind: "student" | "staff";
  id: number;
  name: string;
  class_name: string | null;
  designation: string | null;
  status: "pending_delete" | "deleted";
  delete_requested_at: string | null;
  delete_requested_by: string | null;
  delete_reason: string | null;
  deleted_at: string | null;
  deleted_by: string | null;
}

// ── Templated PDF flow ──────────────────────────────────────────────
export type PdfTemplateKind = "report-card" | "pseb-admit-card";

export type ReportLayout = "summary" | "components";

export interface PdfTemplate {
  id: number;
  kind: PdfTemplateKind;
  class_name: string;
  session: string;
  term: string | null;
  scope: ResultScope | null; // report cards: which results the card prints
  layout: ReportLayout;
  version: number;
  data: Record<string, unknown>;
  created_at: string;
  created_by: string;
  updated_at: string;
  updated_by: string;
}

export interface PdfStudentDataRow {
  student_id: number;
  data: Record<string, unknown>;
  updated_at: string;
  updated_by: string;
}

export interface PdfStudentRosterRow {
  id: number;
  name: string;
  roll_no: string | null;
  has_data: boolean;
  cached_pdf_id: number | null; // a PDF matching what the card would print now
  stale_pdf_id: number | null;  // a PDF exists but something changed since
  has_marks: boolean;
  draft_marks: number;
  provisional: boolean;
  missing_dob: boolean;
  has_photo: boolean;
  has_remarks: boolean;
  house: string | null;
  rank: number | null;
  total: number | null;
  max: number | null;
  percentage: number | null;
  attendance_pct: number | null;
  error: string | null; // why a card can't be produced yet
}

export interface PdfRoster {
  template_id: number;
  scope: ResultScope | null;
  class_size: number;
  warnings: string[];
  students: PdfStudentRosterRow[];
}

export interface PdfRenderResultRow {
  student_id: number;
  status: "cached" | "rendered" | "error";
  pdf_id: number | null;
  error: string | null;
  warnings?: string[];
}

export interface RenderJob {
  id: number;
  template_id: number;
  status: "queued" | "running" | "done" | "failed" | "cancelled";
  total: number;
  done_count: number;
  error_count: number;
  requested_by: string;
  error: string | null;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  results: PdfRenderResultRow[];
}

export interface Bilingual {
  en: string;
  pa?: string | null;
}

/** pdf_templates.data for report cards (backend: ReportCardTemplateData). */
export interface ReportCardTemplateData {
  signatures: { classTeacher?: string | null; examIncharge?: string | null; principal?: string | null };
  showAttendance: boolean;
  showRank: boolean;
  showPhoto: boolean;
  showGradingScale: boolean;
  includeDrafts: boolean;
  promotionRule: { passPct: number; conditionalMaxFails: number };
  remarksDefault: Bilingual | null;
}

/** pdf_student_data.data for report cards (backend: ReportCardStudentData). */
export interface ReportCardStudentData {
  remarks?: Bilingual | null;
  house?: string | null;
  rank?: number | null;
  classSize?: number | null;
  attendancePct?: number | null;
  workingDays?: number | null;
  daysPresent?: number | null;
  promotion?: string | null;
  admissionNo?: string | null;
}

// ── Class-subjects master ─────────────────────────────────────────
export type SubjectCategory = "academic" | "co_curricular" | "grading";

export interface ExamComponent {
  id: number;
  class_subject_id: number;
  component_name: string;
  max_marks: number;
  order_index: number;
  term: number | null; // 1 | 2 | null = both terms
  created_at: string;
  updated_at: string;
}

export interface ClassSubject {
  id: number;
  class_name: string;
  subject_name: string;
  subject_name_pa: string | null;
  category: SubjectCategory;
  order_index: number;
  created_at: string;
  updated_at: string;
}

export interface ClassSubjectDetail extends ClassSubject {
  components: ExamComponent[];
}

// ── Aggregated results (GET /marks/results) ──────────────────────
export type ResultScope = "term1" | "term2" | "annual";
export type BatchStatus = "submitted" | "draft" | "none";
export type CellStatus = "complete" | "partial" | "missing" | "none";

export interface ComponentInfo {
  component_name: string;
  group: string; // "Semester First — Written" → "Semester First"
  term: number | null;
  max: number;
}

export interface SubjectColumn {
  subject_name: string;
  subject_name_pa: string | null;
  category: SubjectCategory;
  order_index: number;
  max: number; // scope max = sum of in-scope component max marks
  is_grading: boolean; // letter-graded subject (max 0)
  batch_status: BatchStatus;
  components: ComponentInfo[];
}

export interface ComponentMark extends ComponentInfo {
  marks: number | null;
  grade_letter: string | null;
  batch_status: "submitted" | "draft" | null;
  counted: boolean;
}

export interface ResultCell {
  key: string;
  obtained: number;
  max: number;
  marked: number;
  total: number;
  status: CellStatus;
}

export interface SubjectResult {
  subject_name: string;
  category: SubjectCategory;
  obtained: number;
  max: number;
  percentage: number | null;
  grade: string | null;
  status: "complete" | "partial" | "missing";
  is_grading: boolean;
  grade_letter: string | null;
  term_letters: Record<string, string>;
  batch_status: BatchStatus;
  components_total: number;
  components_marked: number;
  components: ComponentMark[];
  cells: ResultCell[];
}

export interface AttendanceSummary {
  working_days: number;
  days_present: number;
  pct: number | null;
  counts: Record<string, number>;
}

export interface StudentResult {
  student_id: number;
  name: string;
  roll_no: string | null;
  status: string;
  subjects: SubjectResult[];
  total_obtained: number;
  total_max: number;
  percentage: number | null;
  grade: string | null;
  has_marks: boolean;
  rank: number | null;
  pass_status: "pass" | "fail" | "incomplete" | null;
  failed_subjects: string[];
  promotion: string | null;
  draft_components: number;
  attendance: AttendanceSummary | null;
}

export interface GroupColumn {
  key: string;
  term: number | null;
  order_index: number;
}

export interface ClassResults {
  class_name: string;
  session: string;
  scope: ResultScope;
  subject_columns: SubjectColumn[];
  students: StudentResult[];
  groups: GroupColumn[];
  class_size: number;
  ranked_count: number;
  include_drafts: boolean;
  has_drafts: boolean;
  complete: boolean;
  engine_version: number;
  session_dates: { start: string; end: string } | null;
  warnings: string[];
}

// ── Marks batch + edit-request workflow ──────────────────────────
export type MarksBatchStatus = "draft" | "submitted";
export type MarksEditRequestStatus = "pending" | "approved" | "rejected";

export interface MarksBatchItem {
  id: number;
  student_id: number;
  marks: number;
  grade: string | null; // letter for graded (max 0) exam components
}

export interface MarksBatch {
  id: number;
  class_name: string;
  subject: string;
  exam_type: string;
  session: string;
  max_marks: number;
  status: MarksBatchStatus;
  created_at: string;
  created_by: string;
  submitted_at: string | null;
  submitted_by: string | null;
  updated_at: string;
}

export interface MarksBatchDetail extends MarksBatch {
  items: MarksBatchItem[];
  pending_edit_request_id: number | null;
  last_rejection: string | null;
}

export interface MarksEditRequestItem {
  id: number;
  batch_id: number;
  class_name: string;
  subject: string;
  exam_type: string;
  session: string;
  student_count: number;
  requested_at: string;
  requested_by: string;
  requested_by_role: "admin" | "staff";
  reason: string;
  status: MarksEditRequestStatus;
  reviewed_at: string | null;
  reviewed_by: string | null;
  reject_reason: string | null;
}

// ── Academic sessions (GET /sessions) ────────────────────────────
export interface AcademicSession {
  id: number;
  session: string; // "2026-27"
  starts_on: string; // ISO dates
  ends_on: string;
  term1_start: string;
  term1_end: string;
  term2_start: string;
  term2_end: string;
  is_current: boolean;
  updated_at: string | null;
  updated_by: string;
}

// ── Reference data (GET /meta) ───────────────────────────────────
export interface Meta {
  classes: string[];
  grade_bands: { grade: string; min_pct: number }[];
  grade_legend: { grade: string; range: string }[];
  grade_letters: string[];
  houses: string[];
  promotion_values: string[];
  pass_pct: number;
  conditional_max_fails: number;
  scopes: ResultScope[];
  menu_keys: string[];
}
