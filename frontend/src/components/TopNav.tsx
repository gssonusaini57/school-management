import { NavLink, useLocation } from "react-router-dom";
import { ChevronDown } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { SECTIONS, filterAccessibleSections } from "@/lib/nav-sections";
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
} from "@/components/ui/dropdown-menu";

export function TopNav() {
  const { t } = useTranslation();
  const { user, isAdmin, isSuperAdmin } = useAuth();
  const { pathname } = useLocation();
  const sections = filterAccessibleSections(SECTIONS, user, isAdmin, isSuperAdmin);

  return (
    <nav className="flex h-12 bg-deep-indigo text-white/80 border-b border-white/10 px-4 items-center gap-1 overflow-x-auto">
      {sections.map((sec) => {
        const sectionActive = sec.items.some((it) => pathname === it.to || pathname.startsWith(it.to + "/"));
        return (
          <DropdownMenu key={sec.titleKey}>
            <DropdownMenuTrigger
              className={cn(
                "flex items-center gap-1 px-3 h-9 rounded text-sm font-medium whitespace-nowrap transition-colors outline-none",
                "hover:bg-white/10 hover:text-white focus-visible:ring-2 focus-visible:ring-royal-gold",
                sectionActive ? "text-royal-gold" : "text-white/80",
              )}
            >
              <span>{t(sec.titleKey)}</span>
              <ChevronDown className="h-3.5 w-3.5 opacity-70" />
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start" className="min-w-[14rem]">
              {sec.items.map((it) => {
                const isActive = pathname === it.to || pathname.startsWith(it.to + "/");
                return (
                  <DropdownMenuItem key={it.to} asChild>
                    <NavLink
                      to={it.to}
                      className={cn(
                        "flex w-full items-center gap-2",
                        isActive && "text-royal-gold font-medium",
                      )}
                    >
                      <it.icon className="h-4 w-4" />
                      <span>{t(it.labelKey)}</span>
                    </NavLink>
                  </DropdownMenuItem>
                );
              })}
            </DropdownMenuContent>
          </DropdownMenu>
        );
      })}
    </nav>
  );
}
