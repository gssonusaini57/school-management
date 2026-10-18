---
name: check-logs
description: Read-only log analysis of the TEST instance (school-management-test on 69.62.72.137). Streams 6 sections (service status, journalctl, error.log tail, recent tracebacks, access.log tail, recent 4xx/5xx) to your terminal. Nothing is downloaded or modified. Accepts an optional time window like 30m, 2h, 1d.
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
PROD has the same script: `bash scripts/deploy/prod/check-logs.sh` (same box, unit `school-management`).

## What you get back (6 sections)

1. **Service status** — `systemctl is-active`, last activation timestamp, MainPID, restart count, current memory.
2. **journalctl --since `<window>`** — filtered to systemd lifecycle + ERROR/CRITICAL/WARN/Traceback/Exception lines.
3. **error.log tail (40 lines)** — gunicorn stderr + Python tracebacks.
4. **Recent Python tracebacks** — every `Traceback (most recent call last)` with the 15 lines after it, last 3 shown.
5. **access.log tail (20 lines)** — recent HTTP requests + status codes.
6. **Recent HTTP errors** — last 20 4xx/5xx responses + total count in file.

Nothing is written to the server, nothing is downloaded locally.

## When to use

- Service failing or returning unexpected errors; after a deploy or a `/sync-test-data`; triaging 401/403/500.

For a full archive of logs, use [scripts/deploy/test/download-logs.sh](../../scripts/deploy/test/download-logs.sh).

## Server

- **IP:** `69.62.72.137` · **SSH key:** `~/.ssh/enamfoss_prod`
- **Remote paths read:** `/opt/school-management-test/logs/{error,access}.log`, `journalctl -u school-management-test`
