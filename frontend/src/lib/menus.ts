// Canonical menu permission registry — mirror of backend/app/permissions.py.
// Admin and super-admin always pass `canAccessMenu` regardless of grants;
// only staff are filtered by their `allowed_menus`.

export type MenuKey =
  | "dashboard"
  | "admissions"
  | "students"
  | "students.bulk"
  | "attendance"
  | "marks-entry"
  | "marks-results"
  | "notices"
  | "fees"
  | "reports"
  | "letterheads"
  | "salary-slips"
  | "templates"
  | "class-subjects"
  | "mobile-apps";

export interface MenuKeyMeta {
  label: string;
  defaultStaff: boolean;
}

export const MENU_KEYS: Record<MenuKey, MenuKeyMeta> = {
  "dashboard":      { label: "Dashboard",              defaultStaff: true },
  "admissions":     { label: "New Admission",          defaultStaff: false },
  "students":       { label: "Students",               defaultStaff: true },
  "students.bulk":  { label: "Students · Bulk import", defaultStaff: false },
  "attendance":     { label: "Attendance",             defaultStaff: true },
  "marks-entry":    { label: "Marks Entry",            defaultStaff: true },
  "marks-results":  { label: "Marks Results",          defaultStaff: true },
  "notices":        { label: "Notices",                defaultStaff: true },
  "fees":           { label: "Fees",                   defaultStaff: false },
  "reports":        { label: "Reports",                defaultStaff: false },
  "letterheads":    { label: "Letterheads",            defaultStaff: false },
  "salary-slips":   { label: "Salary Slips",           defaultStaff: false },
  "templates":      { label: "PDF Templates",          defaultStaff: false },
  "class-subjects": { label: "Class Subjects",          defaultStaff: false },
  "mobile-apps":    { label: "Mobile Apps",            defaultStaff: true },
};

export const ALL_MENU_KEYS = Object.keys(MENU_KEYS) as MenuKey[];

export const DEFAULT_STAFF_MENUS: MenuKey[] = ALL_MENU_KEYS.filter(
  (k) => MENU_KEYS[k].defaultStaff,
);
