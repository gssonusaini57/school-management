---
name: feedback_notify_never_raises
description: "Post-commit notification helpers must never break the request; guard with @_never_raises + log. A missing import once 500'd every staff edit-save."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: df87bf8a-36fb-4e09-9510-12bbdd0d215e
---

Session 14 (2026-05-31). The `feat(email)` commit added `notify_student_edit_request(db, req, s)` to `students.py` but FORGOT to import it → `NameError` AFTER the edit request was already committed → every staff/admin student edit-save returned 500 ("works on 2nd click" because the 2nd hit the already-pending 409 branch, which skips the notify call). Confirmed in prod error.log.

**Why:** notifications are best-effort side-effects fired after the DB commit; a bug there (missing import, template render error, SMTP failure) must surface as a logged error, never a 500 on the request that already succeeded.

**How to apply:** every helper in `backend/app/notifications.py` is now wrapped with a `@_never_raises` decorator that try/excepts the WHOLE body (not just the SMTP send inside `_send`) and `log.exception`s. Keep new notify helpers decorated. Don't also add a redundant call-site try/except — the decorated function can't raise, so the call-site guard is dead code (caught in review). Relatedly, watch reserved LogRecord `extra=` keys (Gotcha #12). See [[project_school_management_deployed]].
