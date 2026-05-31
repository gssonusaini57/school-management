"""Workflow email notifications (approval requests + outcomes).

Thin, fail-safe wrappers around `mailer.send_email` + `email_templates`. Every
function:
  - is a no-op when email isn't configured (`settings.email_enabled` is False),
  - swallows ALL exceptions (logs only) so a mail hiccup never breaks the API
    request that triggered it — mirrors routers/auth.py:forgot_password.

Call these AFTER the DB commit + broker.publish in each router.
"""
from __future__ import annotations

import functools

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .config import settings
from .mailer import send_email
from .models.staff import Staff
from .models.record_status import RecordStatus
from . import email_templates as tpl
from .logging_config import get_logger

log = get_logger("app.notifications")


def _never_raises(fn):
    """Guarantee a notification helper can never break its caller.

    Notifications are best-effort side-effects fired AFTER the DB commit. A bug
    anywhere in the helper (template rendering, a missing import, a bad lookup)
    must surface as a logged error — never as a 500 on the request that already
    succeeded. This wraps the WHOLE body, not just the SMTP send, so failures
    before `_send` (e.g. building the email) are caught too.

    Root-caused exactly this in prod: a missing import made the call raise
    NameError, turning every staff/admin edit-save into a 500 (see students.py).
    """
    @functools.wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            log.exception(
                "notification helper failed",
                extra={"event": "notify_failed", "helper": fn.__name__},
            )
            return None
    return wrapper


def _send(to: str, built: tuple[str, str, str], event: str) -> None:
    """Send a (subject, html, text) tuple; never raises."""
    if not settings.email_enabled:
        return
    if not to:
        return
    subject, html, text = built
    try:
        send_email(to=to, subject=subject, html=html, text=text)
        log.info("notification sent", extra={"event": event, "notify_to": to})
    except Exception:
        log.exception("notification send failed", extra={"event": event})


def _staff_email_by_name(db: Session, name: str | None) -> str | None:
    """Best-effort lookup of a staff member's email by display name.

    `requested_by` is a display name (not an ID), so duplicates are possible;
    we take the first active match. Returns None if not found (caller falls
    back to the approver inbox).
    """
    if not name:
        return None
    row = db.execute(
        select(Staff).where(
            func.lower(Staff.name) == name.strip().lower(),
            Staff.status != RecordStatus.deleted,
        )
    ).scalars().first()
    return row.email if row and row.email else None


def _logo() -> str:
    return settings.email_logo_url


def _url(path: str) -> str:
    return f"{settings.APP_BASE_URL.rstrip('/')}{path}"


# ── Approval-needed (→ approver inbox) ──────────────────────────────────────
@_never_raises
def notify_student_edit_request(db: Session, req, student) -> None:
    fields = list((req.changes or {}).keys())
    built = tpl.student_edit_request_email(
        requester=req.requested_by,
        student_name=student.name if student else f"#{req.student_id}",
        class_name=student.class_name if student else None,
        fields=fields,
        review_url=_url("/edit-requests"),
        logo_url=_logo(),
    )
    _send(settings.approver_notify_email, built, "notify_student_edit_request")


@_never_raises
def notify_marks_edit_request(db: Session, req, batch) -> None:
    built = tpl.marks_edit_request_email(
        requester=req.requested_by,
        class_name=batch.class_name,
        subject_name=batch.subject,
        exam_type=batch.exam_type,
        session=batch.session,
        reason=req.reason or "—",
        review_url=_url("/edit-requests"),
        logo_url=_logo(),
    )
    _send(settings.approver_notify_email, built, "notify_marks_edit_request")


@_never_raises
def notify_marks_submitted(db: Session, batch, student_count: int) -> None:
    built = tpl.marks_batch_submitted_email(
        submitter=batch.submitted_by or batch.created_by or "A teacher",
        class_name=batch.class_name,
        subject_name=batch.subject,
        exam_type=batch.exam_type,
        session=batch.session,
        student_count=student_count,
        view_url=_url("/marks/results"),
        logo_url=_logo(),
    )
    _send(settings.approver_notify_email, built, "notify_marks_submitted")


# ── Outcomes (→ original requester, fallback approver inbox) ─────────────────
@_never_raises
def notify_request_outcome(
    db: Session, *, kind: str, outcome: str, requester: str,
    detail: str, reason: str | None = None,
) -> None:
    to = _staff_email_by_name(db, requester) or settings.approver_notify_email
    built = tpl.request_outcome_email(
        recipient_name=requester,
        kind=kind,
        outcome=outcome,
        detail=detail,
        reason=reason,
        review_url=_url("/dashboard"),
        logo_url=_logo(),
    )
    _send(to, built, f"notify_request_{outcome}")
