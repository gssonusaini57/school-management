"""Shared helpers for /api/<entity>/bulk-import endpoints.

All bulk-import routes must be **atomic**: validate every row, and only commit
when the entire file is clean. If any row fails, return `{inserted: 0, errors}`
without writing anything to the DB. The frontend keys off `inserted == 0` to
tell the admin "fix the file and re-upload."

Per-row failures should raise `FieldError(field, value, reason)` so the
response can pinpoint the exact CSV column the admin needs to fix.
"""
import csv
import io
import re
from datetime import date, datetime
from typing import Any, Iterable
from fastapi import UploadFile

# Date formats accepted in CSV imports. ISO is preferred and what the template
# emits, but Excel/Sheets in Indian locale almost always auto-converts ISO
# dates to DD-MM-YYYY or DD/MM/YYYY on save — admins shouldn't have to fight
# their spreadsheet, so we accept those too. Order matters: ISO must come
# first so "2015-08-15" is parsed as YYYY-MM-DD, not interpreted as DD-MM-YYYY.
_DATE_FORMATS: tuple[str, ...] = (
    "%Y-%m-%d",   # 2015-08-15  (template/ISO — preferred)
    "%d-%m-%Y",   # 15-08-2015  (Excel India default)
    "%d/%m/%Y",   # 15/08/2015  (Sheets India default)
    "%d-%m-%y",   # 15-08-15
    "%d/%m/%y",   # 15/08/15
)


class FieldError(ValueError):
    """A validation failure tied to a specific CSV column.

    Carries `field` (CSV header), `value` (the offending cell), and `reason`
    (human-readable explanation) so route handlers can return structured errors.
    """

    def __init__(self, field: str, value: Any, reason: str):
        self.field = field
        self.value = "" if value is None else str(value)
        self.reason = reason
        super().__init__(f"{field}: {reason}")


def parse_csv(file_content: bytes) -> Iterable[dict[str, str]]:
    """Parse a CSV file into a list of dicts. Handles UTF-8 BOM."""
    text = file_content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader)


async def read_csv(file: UploadFile) -> list[dict[str, str]]:
    raw = await file.read()
    if not raw:
        return []
    return list(parse_csv(raw))


def title_case(s: str | None) -> str:
    return " ".join(w.capitalize() for w in (s or "").strip().split())


def parse_date_field(s: str | None, field: str = "date") -> date | None:
    """Parse a CSV date cell into `date`. Empty → None.

    Accepts YYYY-MM-DD (preferred), DD-MM-YYYY, DD/MM/YYYY (and 2-digit-year
    variants) so Excel-converted CSVs Just Work for Indian-locale users.
    Validates month 1–12 and day 1–31 explicitly so the error tells the
    admin which part is wrong rather than the generic strptime message.
    """
    s = (s or "").strip()
    if not s:
        return None

    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue

    # Couldn't match any accepted format. Give a precise reason when possible
    # (e.g. "month must be 1–12 (got 13)") so the admin can fix the cell.
    parts = re.split(r"[-/.]", s)
    if len(parts) == 3 and all(p.strip().isdigit() for p in parts):
        nums = [int(p) for p in parts]
        # First token 4 digits → assume YYYY-MM-DD; else assume DD-MM-YYYY.
        if len(parts[0].strip()) == 4:
            year, month, day = nums
        else:
            day, month, year = nums
            if year < 100:
                year += 2000 if year < 50 else 1900
        if not 1 <= month <= 12:
            raise FieldError(field, s, f"month must be 1–12 (got {month})")
        if not 1 <= day <= 31:
            raise FieldError(field, s, f"day must be 1–31 (got {day})")
        try:
            return date(year, month, day)
        except ValueError as e:
            raise FieldError(field, s, f"invalid date ({e})") from None

    raise FieldError(field, s, "use YYYY-MM-DD or DD-MM-YYYY (e.g. 2015-08-15 or 15-08-2015)")


def must_str(row: dict[str, str], key: str) -> str:
    v = (row.get(key) or "").strip()
    if not v:
        raise FieldError(key, "", "required field is empty")
    return v


def opt_str(row: dict[str, str], key: str, default: str = "") -> str:
    return (row.get(key) or "").strip() or default


def must_int(row: dict[str, str], key: str) -> int:
    raw = must_str(row, key)
    try:
        return int(raw)
    except ValueError:
        raise FieldError(key, raw, "must be a whole number") from None


def opt_int(row: dict[str, str], key: str, default: int) -> int:
    raw = (row.get(key) or "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise FieldError(key, raw, "must be a whole number") from None


def must_choice(row: dict[str, str], key: str, choices: tuple[str, ...]) -> str:
    raw = must_str(row, key)
    if raw not in choices:
        raise FieldError(key, raw, f"must be one of {', '.join(choices)}")
    return raw


def error_dict(row_num: int, exc: BaseException, row: dict[str, str]) -> dict:
    """Build the structured error entry returned to the frontend."""
    if isinstance(exc, FieldError):
        return {
            "row": row_num,
            "field": exc.field,
            "value": exc.value,
            "reason": exc.reason,
            "data": row,
        }
    return {
        "row": row_num,
        "field": None,
        "value": None,
        "reason": str(exc) or exc.__class__.__name__,
        "data": row,
    }
