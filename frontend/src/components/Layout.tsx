import { Outlet, NavLink, useNavigate } from "react-router-dom";
import {
  LayoutDashboard, UserPlus, Users, ClipboardCheck, GraduationCap,
  Wallet, Megaphone, Briefcase, BarChart3, LogOut, Menu, KeyRound, Smartphone,
  FileText, Receipt, FileStack, ShieldAlert,
} from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth, clearAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { ChangePasswordDialog } from "./ChangePasswordDialog";
import { LocaleSwitch } from "./LocaleSwitch";

interface NavItem {
  to: string;
  labelKey: string;
  icon: React.ComponentType<{ className?: string }>;
  adminOnly?: boolean;
  superAdminOnly?: boolean;
}

interface NavSection {
  titleKey: string;
  items: NavItem[];
}

const SECTIONS: NavSection[] = [
  {
    titleKey: "portal.nav.sectionMain",
    items: [
      { to: "/dashboard",  labelKey: "portal.nav.dashboard",    icon: LayoutDashboard },
      { to: "/admissions", labelKey: "portal.nav.newAdmission", icon: UserPlus },
      { to: "/students",   labelKey: "portal.nav.students",     icon: Users },
    ],
  },
  {
    titleKey: "portal.nav.sectionAcademic",
    items: [
      { to: "/attendance",     labelKey: "portal.nav.attendance",   icon: ClipboardCheck },
      { to: "/marks/entry",    labelKey: "portal.nav.marksEntry",   icon: GraduationCap },
      { to: "/marks/results",  labelKey: "portal.nav.marksResults", icon: GraduationCap },
    ],
  },
  {
    titleKey: "portal.nav.sectionAdministration",
    items: [
      { to: "/fees",     labelKey: "portal.nav.fees",     icon: Wallet,    adminOnly: true },
      { to: "/notices",  labelKey: "portal.nav.notices",  icon: Megaphone },
      { to: "/staff",    labelKey: "portal.nav.staff",    icon: Briefcase, adminOnly: true },
      { to: "/reports",  labelKey: "portal.nav.reports",  icon: BarChart3, adminOnly: true },
      { to: "/deletion-requests", labelKey: "portal.nav.deletionRequests", icon: ShieldAlert, superAdminOnly: true },
    ],
  },
  {
    titleKey: "portal.nav.sectionStationery",
    items: [
      { to: "/letterheads",  labelKey: "portal.nav.letterheads", icon: FileText,  adminOnly: true },
      { to: "/salary-slips", labelKey: "portal.nav.salarySlips", icon: Receipt,   adminOnly: true },
      { to: "/templates",    labelKey: "portal.nav.templates",   icon: FileStack, adminOnly: true },
    ],
  },
  {
    titleKey: "portal.nav.sectionResources",
    items: [
      { to: "/mobile-apps", labelKey: "portal.nav.mobileApps", icon: Smartphone },
    ],
  },
];

export function Layout() {
  const { t, i18n } = useTranslation();
  const { user, isAdmin, isSuperAdmin, setUser } = useAuth();
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const [pwdOpen, setPwdOpen] = useState(false);

  const logout = () => {
    clearAuth();
    setUser(null);
    nav("/login", { replace: true });
  };

  const dateLocale = i18n.language === "pa" ? "pa-IN" : "en-IN";

  return (
    <div className="min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          "fixed top-0 left-0 z-40 h-screen w-64 bg-deep-indigo text-white/80 overflow-y-auto transition-transform",
          open ? "translate-x-0" : "-translate-x-full md:translate-x-0"
        )}
      >
        <div className="h-16 flex items-center px-5 border-b border-white/10">
          <div>
            <div className="font-display text-royal-gold font-bold tracking-wide">{t("portal.layout.appName")}</div>
            <div className="text-white/50 text-xs">{t("portal.layout.appTag")}</div>
          </div>
        </div>
        {SECTIONS.map((sec) => {
          const items = sec.items.filter((i) => {
            if (i.superAdminOnly && !isSuperAdmin) return false;
            if (i.adminOnly && !isAdmin) return false;
            return true;
          });
          if (!items.length) return null;
          return (
            <div key={sec.titleKey} className="py-3">
              <div className="px-5 text-[10px] uppercase tracking-widest text-white/40 font-bold mb-1">
                {t(sec.titleKey)}
              </div>
              {items.map((it) => (
                <NavLink
                  key={it.to}
                  to={it.to}
                  onClick={() => setOpen(false)}
                  className={({ isActive }) =>
                    cn(
                      "flex items-center gap-3 px-5 py-2 text-sm border-l-[3px] border-transparent hover:bg-white/5 hover:text-white transition-colors",
                      isActive && "text-royal-gold bg-royal-gold/10 border-royal-gold"
                    )
                  }
                >
                  <it.icon className="h-4 w-4" />
                  <span>{t(it.labelKey)}</span>
                </NavLink>
              ))}
            </div>
          );
        })}
        <div className="p-3 border-t border-white/10 mt-2 space-y-1">
          {isAdmin && (
            <button
              onClick={() => setPwdOpen(true)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded text-sm text-white/60 hover:bg-white/5 hover:text-white"
            >
              <KeyRound className="h-4 w-4" /> {t("portal.layout.changePassword")}
            </button>
          )}
          <button
            onClick={logout}
            className="w-full flex items-center gap-2 px-3 py-2 rounded text-sm text-white/60 hover:bg-destructive/20 hover:text-destructive-foreground"
          >
            <LogOut className="h-4 w-4" /> {t("portal.layout.logout")}
          </button>
        </div>
      </aside>

      {/* Topbar */}
      <header className="fixed top-0 left-0 md:left-64 right-0 h-16 bg-white border-b border-border shadow-sm z-30 flex items-center justify-between px-4 md:px-6">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" className="md:hidden" onClick={() => setOpen((s) => !s)} aria-label={t("portal.layout.menu")}>
            <Menu className="h-5 w-5" />
          </Button>
          <div>
            <div className="text-sm font-semibold">{user?.name}</div>
            <div className="text-xs text-muted-foreground">
              {user?.role === "super_admin"
                ? t("portal.layout.roleSuperAdmin", "Super-Admin")
                : user?.role === "admin"
                  ? t("portal.layout.roleAdmin")
                  : t("portal.layout.roleStaff")}
            </div>
          </div>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground hidden sm:block">
            {new Date().toLocaleDateString(dateLocale, { weekday: "long", day: "2-digit", month: "short", year: "numeric" })}
          </div>
          <LocaleSwitch />
        </div>
      </header>

      {/* Main */}
      <main className="md:ml-64 pt-16 min-h-screen">
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>

      <ChangePasswordDialog open={pwdOpen} onOpenChange={setPwdOpen} />
    </div>
  );
}
