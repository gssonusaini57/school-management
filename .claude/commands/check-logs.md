---
name: check-logs
description: Read-only log analysis on the TEST server. Streams 6 sections (service status, journalctl, error.log tail, recent tracebacks, access.log tail, recent 4xx/5xx) to your terminal. Nothing is downloaded or modified. Accepts an optional time window like 30m, 2h, 1d.
---

# Log analysis → TEST

## Action

```bash
bash scripts/deploy/test/check-logs.sh
# or:
bash scripts/deploy/test/check-logs.sh 30m
bash scripts/deploy/test/check-logs.sh 2h
bash scripts/deploy/test/check-logs.sh '15 minutes ago'
```

If the user includes a duration shorthand like `30m` / `2h` / `1d`, pass it positionally. Otherwise default to `1 hour ago`.

## What you get back (6 sections)

1. **Service status** — `systemctl is-active`, last activation timestamp, MainPID, restart count, current memory.
2. **journalctl --since `<window>`** — filtered to systemd lifecycle + ERROR/CRITICAL/WARN/Traceback/Exception lines. Catches restarts, crashes, OOM kills.
3. **error.log tail (40 lines)** — gunicorn stderr + Python tracebacks.
4. **Recent Python tracebacks** — every `Traceback (most recent call last)` with the 15 lines after it, last 3 shown. Each block prefixed with `---`.
5. **access.log tail (20 lines)** — recent HTTP requests + status codes.
6. **Recent HTTP errors** — last 20 4xx/5xx responses + total count in file.

Nothing is written to the server, nothing is downloaded locally — output streams straight through SSH to your terminal.

## When to use

- Service is failing or returning unexpected errors and you need a fast diagnosis.
- After a deploy, to confirm nothing crashed in the first few minutes.
- Investigating a user-reported 401 / 403 / 500.
- Triaging "is the app even running?".

For a full archive of logs (not just a tail), use [scripts/deploy/test/download-logs.sh](../../scripts/deploy/test/download-logs.sh) — that one writes to a local timestamped folder.

## Server

- **IP:** `104.237.5.113`
- **SSH key:** `~/.ssh/uploadmytds_test`
- **Remote paths read:**
  - `/opt/school-management/logs/error.log`
  - `/opt/school-management/logs/access.log`
  - `journalctl -u school-management`
