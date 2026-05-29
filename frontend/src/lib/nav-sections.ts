import {
  LayoutDashboard, UserPlus, Users, ClipboardCheck, GraduationCap,
  Wallet, Megaphone, Briefcase, BarChart3, Smartphone,
  FileText, Receipt, FileStack, ShieldAlert, FileEdit, BookOpen,
} from "lucide-react";
import type { MenuKey } from "@/lib/menus";
import { canAccessMenu, type AuthUser } from "@/lib/auth";

export interface NavItem {
  to: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  superAdminOnly?: boolean;
  menuKey?: MenuKey;
}

export interface NavSection {
  titleKey: string;
  items: NavItem[];
}

export const SECTIONS: NavSection[] = [
  {
    titleKey: "portal.nav.sectionMain",
    items: [
      { to: "/dashboard",  labelKey: "portal.nav.dashboard",    icon: LayoutDashboard, menuKey: "dashboard" },
      { to: "/admissions", labelKey: "portal.nav.newAdmission", icon: UserPlus,        menuKey: "admissions" },
      { to: "/students",   labelKey: "portal.nav.students",     icon: Users,           menuKey: "students" },
    ],
  },
  {
    titleKey: "portal.nav.sectionAcademic",
    items: [
      { to: "/attendance",     labelKey: "portal.nav.attendance",   icon: ClipboardCheck, menuKey: "attendance" },
      { to: "/marks/entry",    labelKey: "portal.nav.marksEntry",   icon: GraduationCap,  menuKey: "marks-entry" },
      { to: "/marks/results",  labelKey: "portal.nav.marksResults", icon: GraduationCap,  menuKey: "marks-results" },
      { to: "/class-subjects", labelKey: "portal.nav.classSubjects", icon: BookOpen,      superAdminOnly: true },
    ],
  },
  {
    titleKey: "portal.nav.sectionAdministration",
    items: [
      { to: "/fees",     labelKey: "portal.nav.fees",     icon: Wallet,    menuKey: "fees" },
      { to: "/notices",  labelKey: "portal.nav.notices",  icon: Megaphone, menuKey: "notices" },
      { to: "/staff",    labelKey: "portal.nav.staff",    icon: Briefcase, adminOnly: true },
      { to: "/reports",  labelKey: "portal.nav.reports",  icon: BarChart3, menuKey: "reports" },
      { to: "/deletion-requests", labelKey: "portal.nav.deletionRequests", icon: ShieldAlert, superAdminOnly: true },
      { to: "/edit-requests",     labelKey: "portal.nav.editRequests",     icon: FileEdit,    superAdminOnly: true },
    ],
  },
  {
    titleKey: "portal.nav.sectionStationery",
    items: [
      { to: "/letterheads",  labelKey: "portal.nav.letterheads", icon: FileText,  menuKey: "letterheads" },
      { to: "/salary-slips", labelKey: "portal.nav.salarySlips", icon: Receipt,   menuKey: "salary-slips" },
      { to: "/templates",    labelKey: "portal.nav.templates",   icon: FileStack, menuKey: "templates" },
    ],
  },
  {
    titleKey: "portal.nav.sectionResources",
    items: [
      { to: "/mobile-apps", labelKey: "portal.nav.mobileApps", icon: Smartphone, menuKey: "mobile-apps" },
    ],
  },
];

export function filterAccessibleSections(
  sections: NavSection[],
  user: AuthUser | null,
  isAdmin: boolean,
  isSuperAdmin: boolean,
): NavSection[] {
  return sections
    .map((sec) => ({
      ...sec,
      items: sec.items.filter((i) => {
        if (i.superAdminOnly && !isSuperAdmin) return false;
        if (i.adminOnly && !isAdmin) return false;
        if (i.menuKey && !canAccessMenu(user, i.menuKey)) return false;
        return true;
      }),
    }))
    .filter((sec) => sec.items.length > 0);
}
