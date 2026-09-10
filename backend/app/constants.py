"""Shared constants for the backend.

Kept in sync with the frontend `CLASSES` list in
`frontend/src/lib/utils.ts` and the Android class list.
"""

# Canonical, ordered list of every class in the school. Single source of truth
# on the backend for the "All classes" sentinel expansion (see `expand_classes`).
CLASSES: list[str] = [
    "Nursery", "L.K.G", "U.K.G",
    "1st", "2nd", "3rd", "4th", "5th", "6th",
    "7th", "8th", "9th", "10th", "11th", "12th",
]


def is_all_sentinel(name: str | None) -> bool:
    """True when a stored class name is the "all classes" sentinel."""
    return (name or "").strip().lower() == "all"


def expand_classes(names: list[str]) -> list[str]:
    """Expand the "All" sentinel to the full class list.

    Staff assigned every class are stored as a single sentinel row
    `class_name="All"` (see staff bulk-import + the frontend collapse-to-["All"]
    rule). Clients (Android app, web portal class pickers) need the concrete list,
    not the literal "All", so expand it here whenever a logged-in user's scope is
    built. A list without the sentinel is returned unchanged.
    """
    if any(is_all_sentinel(n) for n in names):
        return list(CLASSES)
    return list(names)
