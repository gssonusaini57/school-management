---
name: logrecord-extra-reserved
description: "Python logging `extra={...}` cannot use reserved LogRecord attribute names (name, msg, args, levelname, message, …) or it raises KeyError on every log call."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 54def71b-6fc2-4765-be47-339a6860ef84
---

Never pass any of these keys via `log.info(..., extra={...})` in Python logging:

`name`, `msg`, `args`, `levelname`, `levelno`, `pathname`, `filename`, `module`, `exc_info`, `exc_text`, `stack_info`, `lineno`, `funcName`, `created`, `msecs`, `relativeCreated`, `thread`, `threadName`, `processName`, `process`, `message`.

The default `Logger.makeRecord()` at `logging/__init__.py:1656` raises a hard `KeyError("Attempt to overwrite %r in LogRecord" % key)` when any of these collide with built-in LogRecord attributes.

**Why:** in Session 9 of school-management this bug was live for 8 days — `extra={"name": s.name, ...}` in students/staff routers crashed every student-create + delete *after* the DB commit, so users got 500s but the row was already written (silent data hazard). Fix: rename the key to `student_name` / `staff_name` / `entity_name`. Caught only because the new [[slash-commands-inventory]] `/check-logs` surfaced the error.log traceback.

**How to apply:** for any new `extra={...}` dict, prefix domain keys (`student_name`, `request_id`, `actor`). Never use bare `name`. Linter would catch this with `pylint logging-format-interpolation` rules, but this repo doesn't run pylint — rely on code review or the `/check-logs` post-deploy sweep instead.
