import { Outlet, useNavigate } from "react-router-dom";
import { LogOut, Menu, KeyRound, ChevronDown } from "lucide-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useAuth, clearAuth } from "@/lib/auth";
import { useNavMode } from "@/lib/nav-mode";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";
import { ChangePasswordDialog } from "./ChangePasswordDialog";
import { LocaleSwitch } from "./LocaleSwitch";
import { Sidebar } from "./Sidebar";
import { TopNav } from "./TopNav";

export function Layout() {
  const { t, i18n } = useTranslation();
  const { user, isAdmin, setUser } = useAuth();
  const nav = useNavigate();
  const { mode, toggle } = useNavMode();
  const [mobileOpen, setMobileOpen] = useState(false);
  const [pwdOpen, setPwdOpen] = useState(false);

  const logout = () => {
    clearAuth();
    setUser(null);
    nav("/login", { replace: true });
  };

  const onHamburger = () => {
    if (typeof window !== "undefined" && window.matchMedia("(min-width: 768px)").matches) {
      toggle();
    } else {
      setMobileOpen((s) => !s);
    }
  };

  const dateLocale = i18n.language === "pa" ? "pa-IN" : "en-IN";
  const sidebarVisibleOnDesktop = mode === "sidebar";
  const showTopNav = mode === "topbar";

  return (
    <div className="min-h-screen bg-background">
      <Sidebar
        open={mobileOpen}
        visibleOnDesktop={sidebarVisibleOnDesktop}
        onItemClick={() => setMobileOpen(false)}
        onChangePassword={() => setPwdOpen(true)}
        onLogout={logout}
      />

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-30 bg-black/40 md:hidden"
          onClick={() => setMobileOpen(false)}
          aria-hidden="true"
        />
      )}

      {/* Slim topbar */}
      <header
        className={cn(
          "fixed top-0 right-0 left-0 h-16 bg-white border-b border-border shadow-sm z-40 flex items-center justify-between px-4 md:px-6 transition-[left]",
          sidebarVisibleOnDesktop && "md:left-64",
        )}
      >
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={onHamburger}
            aria-label={t("portal.layout.menu")}
          >
            <Menu className="h-5 w-5" />
          </Button>
          <DropdownMenu>
            <DropdownMenuTrigger className="flex items-center gap-2 px-2 py-1 rounded hover:bg-muted/60 outline-none focus-visible:ring-2 focus-visible:ring-ring text-left">
              <div>
                <div className="text-sm font-semibold leading-tight">{user?.name}</div>
                <div className="text-xs text-muted-foreground leading-tight">
                  {user?.role === "super_admin"
                    ? t("portal.layout.roleSuperAdmin", "Super-Admin")
                    : user?.role === "admin"
                      ? t("portal.layout.roleAdmin")
                      : t("portal.layout.roleStaff")}
                </div>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[14rem]">
              {isAdmin && (
                <DropdownMenuItem onSelect={() => setPwdOpen(true)}>
                  <KeyRound className="h-4 w-4" />
                  <span>{t("portal.layout.changePassword")}</span>
                </DropdownMenuItem>
              )}
              {isAdmin && <DropdownMenuSeparator />}
              <DropdownMenuItem onSelect={logout} className="text-destructive focus:text-destructive">
                <LogOut className="h-4 w-4" />
                <span>{t("portal.layout.logout")}</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-sm text-muted-foreground hidden sm:block">
            {new Date().toLocaleDateString(dateLocale, { weekday: "long", day: "2-digit", month: "short", year: "numeric" })}
          </div>
          <LocaleSwitch />
          <Button
            variant="ghost"
            size="sm"
            onClick={logout}
            className="text-destructive hover:text-destructive hover:bg-destructive/10"
            aria-label={t("portal.layout.logout")}
          >
            <LogOut className="h-4 w-4" />
            <span className="hidden sm:inline ml-2">{t("portal.layout.logout")}</span>
          </Button>
        </div>
      </header>

      {/* Desktop top-nav strip (topbar mode only) */}
      {showTopNav && (
        <div className="fixed top-16 right-0 left-0 z-30 hidden md:block">
          <TopNav />
        </div>
      )}

      {/* Main */}
      <main
        className={cn(
          "min-h-screen pt-16",
          sidebarVisibleOnDesktop && "md:ml-64",
          showTopNav && "md:pt-28",
        )}
      >
        <div className="p-4 md:p-6">
          <Outlet />
        </div>
      </main>

      <ChangePasswordDialog open={pwdOpen} onOpenChange={setPwdOpen} />
    </div>
  );
}
