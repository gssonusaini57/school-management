"""HTML email templates for transactional mail.

Email clients are hostile to modern CSS, so everything here uses table layout
+ inline styles. KIS brand palette is hard-coded (deep indigo / khalsa blue /
royal gold on parchment) since email can't reference the design-system tokens.

Every template returns a `(subject, html, text)` tuple and accepts a `logo_url`.
The shared `_email_shell` renders the tri-band header (with crest), the white
card body, and the footer — so each template only supplies its heading + body.
"""
from html import escape

# Brand palette (mirrors packages/design-system/tokens.css; inlined for email).
DEEP_INDIGO = "#08205C"
KHALSA_BLUE = "#0E2F8E"
ROYAL_GOLD = "#F5C518"
PARCHMENT = "#FFF6CC"   # vasant-cream
INK = "#1A1A1A"
MUTED = "#6B6B72"       # neutral-500
SUCCESS = "#15803D"
ERROR = "#E11D2C"

SCHOOL_NAME = "Khalsa International School"
PORTAL_TAG = "Student Management Portal"
SUPPORT_NOTE = (
    "If you didn't request a password reset, you can safely ignore this email "
    "— your password will stay the same."
)
AUTOMATED_NOTE = (
    f"This is an automated message from {SCHOOL_NAME}.<br />"
    "Please do not reply to this email."
)


def _logo_block(logo_url: str) -> str:
    """Crest in a white rounded tile so it stays visible on the dark header.

    The KIS crest PNG is 5:4 landscape (gotcha #11) — keep the aspect ratio
    with an explicit width/height. Returns "" when no logo URL is configured,
    so the header degrades gracefully to the text wordmark.
    """
    if not logo_url:
        return ""
    return f"""\
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 14px;">
                <tr>
                  <td style="background:#ffffff;border-radius:12px;padding:10px 14px;">
                    <img src="{logo_url}" alt="{SCHOOL_NAME}" width="80" height="64"
                         style="display:block;height:64px;width:auto;border:0;outline:none;text-decoration:none;" />
                  </td>
                </tr>
              </table>"""


def _email_shell(*, subject: str, heading: str, body_html: str, logo_url: str,
                 heading_color: str = DEEP_INDIGO, footer_note: str = AUTOMATED_NOTE) -> str:
    """Wrap body content in the standard KIS branded email chrome."""
    logo_html = _logo_block(logo_url)
    return f"""\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta name="color-scheme" content="light only" />
  <title>{escape(subject)}</title>
</head>
<body style="margin:0;padding:0;background:{PARCHMENT};">
  <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PARCHMENT};padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px;width:100%;background:#ffffff;border:1px solid #e7e1d3;border-radius:12px;overflow:hidden;font-family:Helvetica,Arial,sans-serif;">
          <!-- Brand header (tri-band) -->
          <tr><td style="height:5px;background:{ROYAL_GOLD};font-size:0;line-height:0;">&nbsp;</td></tr>
          <tr>
            <td style="background:{DEEP_INDIGO};padding:28px 32px;text-align:center;">
{logo_html}
              <div style="color:#ffffff;font-size:20px;font-weight:700;letter-spacing:0.5px;">{SCHOOL_NAME}</div>
              <div style="color:{ROYAL_GOLD};font-size:11px;letter-spacing:3px;text-transform:uppercase;margin-top:6px;">{PORTAL_TAG}</div>
            </td>
          </tr>
          <tr><td style="height:3px;background:{ROYAL_GOLD};font-size:0;line-height:0;">&nbsp;</td></tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px;">
              <h1 style="margin:0 0 16px;color:{heading_color};font-size:22px;font-weight:700;">{escape(heading)}</h1>
{body_html}
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:{PARCHMENT};padding:20px 32px;text-align:center;border-top:1px solid #ece7da;">
              <div style="color:{MUTED};font-size:12px;line-height:1.6;">
                {footer_note}
              </div>
            </td>
          </tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _p(text: str) -> str:
    return f'<p style="margin:0 0 16px;color:{INK};font-size:15px;line-height:1.6;">{text}</p>'


def _button(url: str, label: str, color: str = KHALSA_BLUE) -> str:
    return f"""\
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 auto 24px;">
                <tr>
                  <td align="center" style="border-radius:8px;background:{color};">
                    <a href="{escape(url, quote=True)}"
                       style="display:inline-block;padding:14px 32px;color:#ffffff;font-size:15px;font-weight:700;text-decoration:none;border-radius:8px;">
                      {escape(label)}
                    </a>
                  </td>
                </tr>
              </table>"""


def _details(rows: list[tuple[str, str]]) -> str:
    """Render a label/value table for the entity details in a notification."""
    trs = "".join(
        f"""\
                <tr>
                  <td style="padding:6px 12px 6px 0;color:{MUTED};font-size:13px;vertical-align:top;white-space:nowrap;">{escape(label)}</td>
                  <td style="padding:6px 0;color:{INK};font-size:14px;font-weight:600;">{escape(value)}</td>
                </tr>"""
        for label, value in rows
    )
    return f"""\
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;background:{PARCHMENT};border-radius:8px;padding:8px 16px;width:100%;">
                {trs}
              </table>"""


# ── Password reset (existing) ──────────────────────────────────────────────
def password_reset_email(
    *, recipient_name: str, reset_url: str, ttl_minutes: int, logo_url: str = ""
) -> tuple[str, str, str]:
    """Return (subject, html, text) for the password-reset email."""
    subject = f"Reset your {SCHOOL_NAME} password"
    greeting = f"Hello {recipient_name}," if recipient_name else "Hello,"

    text = (
        f"{greeting}\n\n"
        f"We received a request to reset the password for your {SCHOOL_NAME} account.\n\n"
        f"Reset your password using the link below (valid for {ttl_minutes} minutes):\n"
        f"{reset_url}\n\n"
        f"{SUPPORT_NOTE}\n\n"
        f"— {SCHOOL_NAME}"
    )

    body = f"""\
              {_p(escape(greeting))}
              {_p(f"We received a request to reset the password for your {SCHOOL_NAME} account. Click the button below to choose a new password.")}
{_button(reset_url, "Reset password")}
              <p style="margin:0 0 8px;color:{MUTED};font-size:13px;line-height:1.6;">
                This link is valid for <strong>{ttl_minutes} minutes</strong>. If the button doesn't work,
                copy and paste this URL into your browser:
              </p>
              <p style="margin:0 0 24px;word-break:break-all;">
                <a href="{escape(reset_url, quote=True)}" style="color:{KHALSA_BLUE};font-size:13px;">{escape(reset_url)}</a>
              </p>
              <hr style="border:none;border-top:1px solid #ece7da;margin:0 0 16px;" />
              <p style="margin:0;color:{MUTED};font-size:13px;line-height:1.6;">{SUPPORT_NOTE}</p>"""

    html = _email_shell(subject=subject, heading="Reset your password", body_html=body, logo_url=logo_url)
    return subject, html, text


# ── Approval-needed notifications (→ approver) ──────────────────────────────
def student_edit_request_email(
    *, requester: str, student_name: str, class_name: str | None,
    fields: list[str], review_url: str, logo_url: str = ""
) -> tuple[str, str, str]:
    subject = f"Approval needed: student edit for {student_name}"
    field_list = ", ".join(fields) if fields else "—"
    cls = class_name or "—"

    text = (
        f"{requester} has requested an edit to a student record and needs your approval.\n\n"
        f"Student: {student_name}\nClass: {cls}\nFields: {field_list}\nRequested by: {requester}\n\n"
        f"Review it here: {review_url}\n\n— {SCHOOL_NAME}"
    )
    body = f"""\
              {_p(f"<strong>{escape(requester)}</strong> has requested an edit to a student record and needs super-admin approval.")}
{_details([("Student", student_name), ("Class", cls), ("Fields", field_list), ("Requested by", requester)])}
{_button(review_url, "Review request")}
              {_p('Open the Edit Requests queue to approve or reject this change.')}"""
    html = _email_shell(subject=subject, heading="Student edit — approval needed", body_html=body, logo_url=logo_url)
    return subject, html, text


def marks_edit_request_email(
    *, requester: str, class_name: str, subject_name: str, exam_type: str,
    session: str, reason: str, review_url: str, logo_url: str = ""
) -> tuple[str, str, str]:
    subject = f"Approval needed: marks edit for {class_name} · {subject_name}"

    text = (
        f"{requester} has requested to unlock a submitted marks batch and needs your approval.\n\n"
        f"Class: {class_name}\nSubject: {subject_name}\nExam: {exam_type}\nSession: {session}\n"
        f"Requested by: {requester}\nReason: {reason}\n\n"
        f"Review it here: {review_url}\n\n— {SCHOOL_NAME}"
    )
    body = f"""\
              {_p(f"<strong>{escape(requester)}</strong> has requested to unlock a submitted marks batch and needs super-admin approval.")}
{_details([("Class", class_name), ("Subject", subject_name), ("Exam", exam_type), ("Session", session), ("Requested by", requester), ("Reason", reason)])}
{_button(review_url, "Review request")}
              {_p('Approving flips the batch back to draft so the teacher can edit and re-submit.')}"""
    html = _email_shell(subject=subject, heading="Marks edit — approval needed", body_html=body, logo_url=logo_url)
    return subject, html, text


def marks_batch_submitted_email(
    *, submitter: str, class_name: str, subject_name: str, exam_type: str,
    session: str, student_count: int, view_url: str, logo_url: str = ""
) -> tuple[str, str, str]:
    subject = f"Marks submitted: {class_name} · {subject_name} ({exam_type})"

    text = (
        f"{submitter} has submitted (locked) a marks batch.\n\n"
        f"Class: {class_name}\nSubject: {subject_name}\nExam: {exam_type}\nSession: {session}\n"
        f"Students: {student_count}\nSubmitted by: {submitter}\n\n"
        f"View results: {view_url}\n\n— {SCHOOL_NAME}"
    )
    body = f"""\
              {_p(f"<strong>{escape(submitter)}</strong> has submitted and locked a marks batch.")}
{_details([("Class", class_name), ("Subject", subject_name), ("Exam", exam_type), ("Session", session), ("Students", str(student_count)), ("Submitted by", submitter)])}
{_button(view_url, "View results")}"""
    html = _email_shell(subject=subject, heading="Marks batch submitted", body_html=body, logo_url=logo_url)
    return subject, html, text


# ── Outcome notifications (→ requester) ─────────────────────────────────────
def request_outcome_email(
    *, recipient_name: str, kind: str, outcome: str, detail: str,
    reason: str | None, review_url: str, logo_url: str = ""
) -> tuple[str, str, str]:
    """One template for all approve/reject outcomes.

    kind: human label of what was reviewed (e.g. "student edit", "marks edit").
    outcome: "approved" or "rejected".
    detail: short context line (e.g. student name, or "Class 8 · Maths").
    """
    approved = outcome == "approved"
    accent = SUCCESS if approved else ERROR
    subject = f"Your {kind} request was {outcome}"
    greeting = f"Hello {recipient_name}," if recipient_name else "Hello,"

    reason_text = f"\nReason: {reason}" if (reason and not approved) else ""
    text = (
        f"{greeting}\n\n"
        f"Your {kind} request ({detail}) was {outcome} by the super-admin.{reason_text}\n\n"
        f"Open the portal: {review_url}\n\n— {SCHOOL_NAME}"
    )

    reason_block = ""
    if reason and not approved:
        reason_block = f"""\
              <table role="presentation" cellpadding="0" cellspacing="0" style="margin:0 0 24px;background:#fdecec;border-radius:8px;padding:12px 16px;width:100%;">
                <tr><td style="color:{ERROR};font-size:13px;font-weight:600;padding-bottom:4px;">Reason</td></tr>
                <tr><td style="color:{INK};font-size:14px;line-height:1.5;">{escape(reason)}</td></tr>
              </table>"""

    body = f"""\
              {_p(escape(greeting))}
              {_p(f'Your <strong>{escape(kind)}</strong> request (<strong>{escape(detail)}</strong>) was <strong style="color:{accent};">{escape(outcome)}</strong> by the super-admin.')}
{reason_block}
{_button(review_url, "Open portal")}"""
    html = _email_shell(
        subject=subject, heading=f"Request {outcome}", body_html=body,
        logo_url=logo_url, heading_color=accent,
    )
    return subject, html, text
