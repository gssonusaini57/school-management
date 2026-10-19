"""Shared constants for the backend.

Kept in sync with the frontend `CLASSES` list in
`frontend/src/lib/utils.ts` and the Android class list.
"""
import re

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


def fold_name(name: str | None) -> str:
    """A name the way MySQL's case-insensitive collation compares it. Rows read
    back for "L.K.G" may spell it "l.k.g", so code that maps database rows onto
    requested names matches them on this key."""
    return (name or "").strip().casefold()


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


# Student houses, as defined by the brand handoff's report-card schema.
HOUSES: tuple[str, ...] = ("Ravidas", "Tagore", "Bhagat Singh", "Nanak")


def _class_key(name: str) -> str:
    return re.sub(r"[\s.]", "", name).lower()


_CLASS_BY_KEY: dict[str, str] = {_class_key(c): c for c in CLASSES}


def canonical_class(name: str | None) -> str | None:
    """Return the canonical spelling of a class name, or None if it is not a class.

    Matching ignores case, spaces and dots, so "LKG", "l.k.g." and "L K G" all
    resolve to "L.K.G". Every write path that stores a `class_name` runs it, so a
    bulk import can never again create a parallel non-canonical class (35 "LKG"
    rows reached prod that way). The "All" sentinel is not a class: it returns None.
    """
    if name is None:
        return None
    return _CLASS_BY_KEY.get(_class_key(name))
