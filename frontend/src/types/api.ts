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

export interface PdfTemplate {
  id: number;
  kind: PdfTemplateKind;
  class_name: string;
  session: string;
  term: string | null;
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
  has_data: boolean;
  cached_pdf_id: number | null;
}

export interface PdfRenderResultRow {
  student_id: number;
  status: "cached" | "rendered" | "error";
  pdf_id: number | null;
  error: string | null;
}

// ── Class-subjects master ─────────────────────────────────────────
export type SubjectCategory = "academic" | "co_curricular" | "grading";

export interface ExamComponent {
  id: number;
  class_subject_id: number;
  component_name: string;
  max_marks: number;
  order_index: number;
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

// ── Marks batch + edit-request workflow ──────────────────────────
export type MarksBatchStatus = "draft" | "submitted";
export type MarksEditRequestStatus = "pending" | "approved" | "rejected";

export interface MarksBatchItem {
  id: number;
  student_id: number;
  marks: number;
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
