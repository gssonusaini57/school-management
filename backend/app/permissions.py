"""Canonical registry of menu permission keys.

Single source of truth for which sidebar/route keys can be granted to a staff
member. Admin and super-admin always pass `is_allowed_for_user` regardless of
the staff's `allowed_menus` field — the granular grants only affect the staff
role.

Mirrored on the frontend at `frontend/src/lib/menus.ts`; keep the two lists
in sync by hand (small enough that a generator isn't worth it yet).
"""
from typing import TypedDict


class MenuKeyMeta(TypedDict):
    label: str
    default_staff: bool


MENU_KEYS: dict[str, MenuKeyMeta] = {
    "dashboard":        {"label": "Dashboard",                "default_staff": True},
    "admissions":       {"label": "New Admission",            "default_staff": False},
    "students":         {"label": "Students",                 "default_staff": True},
    "students.bulk":    {"label": "Students · Bulk import",   "default_staff": False},
    "attendance":       {"label": "Attendance",               "default_staff": True},
    "marks-entry":      {"label": "Marks Entry",              "default_staff": True},
    "marks-results":    {"label": "Marks Results",            "default_staff": True},
    "notices":          {"label": "Notices",                  "default_staff": True},
    "fees":             {"label": "Fees",                     "default_staff": False},
    "reports":          {"label": "Reports",                  "default_staff": False},
    "letterheads":      {"label": "Letterheads",              "default_staff": False},
    "salary-slips":     {"label": "Salary Slips",             "default_staff": False},
    "templates":        {"label": "PDF Templates",            "default_staff": False},
    "class-subjects":   {"label": "Class Subjects",            "default_staff": False},
    "mobile-apps":      {"label": "Mobile Apps",              "default_staff": True},
}

DEFAULT_STAFF_MENUS: list[str] = [k for k, v in MENU_KEYS.items() if v["default_staff"]]


def is_valid_menu_key(key: str) -> bool:
    return key in MENU_KEYS


def sanitize_menus(keys: list[str] | None) -> list[str]:
    """Deduplicate + drop unknown keys. Used at create/update time."""
    if not keys:
        return list(DEFAULT_STAFF_MENUS)
    seen: set[str] = set()
    out: list[str] = []
    for k in keys:
        if k in MENU_KEYS and k not in seen:
            seen.add(k)
            out.append(k)
    return out
