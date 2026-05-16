"""Formatting helpers used inside Jinja templates as filters.

Mirrors frontend/src/lib/format.ts so the React portal and the print
templates render identical strings for the same inputs.
"""
from datetime import date, datetime


def format_inr(amount: float | int, fraction: int = 2) -> str:
    """Indian-grouping currency: ₹ 1,00,000.00.

    Python's locale module is unreliable inside a server (relies on system
    locale being installed) so we hand-roll the grouping.
    """
    if amount is None:
        return ""
    neg = amount < 0
    n = abs(float(amount))
    int_part = int(n)
    frac = n - int_part
    s = str(int_part)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        formatted = ",".join(groups) + "," + tail
    else:
        formatted = s
    if fraction > 0:
        frac_str = f"{frac:.{fraction}f}".split(".")[1]
        formatted = f"{formatted}.{frac_str}"
    return f"{'−' if neg else ''}₹ {formatted}"


def _parse(d: str | date | datetime) -> date:
    if isinstance(d, datetime):
        return d.date()
    if isinstance(d, date):
        return d
    return datetime.strptime(d, "%Y-%m-%d").date()


_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def format_date_long(d: str | date | datetime) -> str:
    """Default date format — `08 May 2026`. Used everywhere except PSEB docs."""
    if not d:
        return ""
    dt = _parse(d)
    return f"{dt.day:02d} {_MONTHS_EN[dt.month - 1]} {dt.year}"


def format_date_pseb(d: str | date | datetime) -> str:
    """PSEB-mandated format — `08-05-2026`. Used on admit cards / date sheets."""
    if not d:
        return ""
    dt = _parse(d)
    return f"{dt.day:02d}-{dt.month:02d}-{dt.year}"


_MONTHS_LONG = ["January", "February", "March", "April", "May", "June",
                "July", "August", "September", "October", "November", "December"]


def format_month_label(ym: str) -> str:
    """Take "2026-04" → "April 2026". Used on salary slips."""
    if not ym:
        return ""
    try:
        y, m = ym.split("-")
        idx = int(m) - 1
        return f"{_MONTHS_LONG[idx]} {y}"
    except (ValueError, IndexError):
        return ym
