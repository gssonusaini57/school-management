// Human-readable labels for Student model field keys. Used by the EditRequests
// diff dialog and could be reused by any future audit-log view.

export const STUDENT_FIELD_LABELS: Record<string, string> = {
  name: "Name",
  father: "Father's Name",
  mother: "Mother's Name",
  dob: "Date of Birth",
  gender: "Gender",
  village: "Village",
  phone: "Phone",
  aadhar: "Aadhaar",
  alt_phone: "Alt. Phone",
  religion: "Religion",
  prev_school: "Previous School",
  bank_name: "Bank Name",
  bank_acc: "Bank A/c",
  bank_ifsc: "Bank IFSC",
  annual_fee: "Annual Fee",
  class_name: "Class",
  admission_no: "Admission No.",
  roll_no: "Roll No.",
};

export function fieldLabel(key: string): string {
  return STUDENT_FIELD_LABELS[key] ?? key;
}

export function diffValue(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "string") return v;
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  try {
    return JSON.stringify(v);
  } catch {
    return String(v);
  }
}
