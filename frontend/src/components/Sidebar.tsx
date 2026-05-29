import { NavLink } from "react-router-dom";
import { LogOut, KeyRound } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { SECTIONS, filterAccessibleSections } from "@/lib/nav-sections";

interface SidebarProps {
  open: boolean;
  visibleOnDesktop: boolean;
  onItemClick: () => void;
  onChangePassword: () => void;
  onLogout: () => void;
}

export function Sidebar({
  open,
  visibleOnDesktop,
  onItemClick,
  onChangePassword,
  onLogout,
}: SidebarProps) {
  const { t } = useTranslation();
  const { user, isAdmin, isSuperAdmin } = useAuth();
  const sections = filterAccessibleSections(SECTIONS, user, isAdmin, isSuperAdmin);

  return (
    <aside
      className={cn(
        "fixed top-0 left-0 z-40 h-screen w-64 bg-deep-indigo text-white/80 overflow-y-auto transition-transform",
        open ? "translate-x-0" : "-translate-x-full",
        visibleOnDesktop && "md:translate-x-0",
      )}
    >
      <div className="h-16 flex items-center px-5 border-b border-white/10">
        <div>
          <div className="font-display text-royal-gold font-bold tracking-wide">
            {t("portal.layout.appName")}
          </div>
          <div className="text-white/50 text-xs">{t("portal.layout.appTag")}</div>
        </div>
      </div>
      {sections.map((sec) => (
        <div key={sec.titleKey} className="py-3">
          <div className="px-5 text-[10px] uppercase tracking-widest text-white/40 font-bold mb-1">
            {t(sec.titleKey)}
          </div>
          {sec.items.map((it) => (
            <NavLink
              key={it.to}
              to={it.to}
              onClick={onItemClick}
              className={({ isActive }) =>
                cn(
                  "flex items-center gap-3 px-5 py-2 text-sm border-l-[3px] border-transparent hover:bg-white/5 hover:text-white transition-colors",
                  isActive && "text-royal-gold bg-royal-gold/10 border-royal-gold",
                )
              }
            >
              <it.icon className="h-4 w-4" />
              <span>{t(it.labelKey)}</span>
            </NavLink>
          ))}
        </div>
      ))}
      <div className="p-3 border-t border-white/10 mt-2 space-y-1">
        {isAdmin && (
          <button
            onClick={onChangePassword}
            className="w-full flex items-center gap-2 px-3 py-2 rounded text-sm text-white/60 hover:bg-white/5 hover:text-white"
          >
            <KeyRound className="h-4 w-4" /> {t("portal.layout.changePassword")}
          </button>
        )}
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-3 py-2 rounded text-sm text-white/60 hover:bg-destructive/20 hover:text-destructive-foreground"
        >
          <LogOut className="h-4 w-4" /> {t("portal.layout.logout")}
        </button>
      </div>
    </aside>
  );
}
