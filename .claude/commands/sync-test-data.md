---
name: sync-test-data
description: Replace the TEST database with a fresh clone of PROD (same server, one SSH session, data never leaves the box), then migrate it to the code deployed on TEST and restart. Destructive for TEST data only; PROD is only read.
---

# Clone PROD data → TEST

## Pre-conditions

- The TEST instance is provisioned (`/provision-test`) and deployed at least once (`/deploy-test-all`).

## Action

1. Tell the user what happens: **every table in `school_management_test` is dropped and replaced**
   with a consistent snapshot of `school_management` (prod is read with
   `mysqldump --single-transaction` — no locks); the test service stops for ~30 s.
   Anything entered on TEST since the last sync is lost (a pre-sync backup is kept).
2. Ask the user to confirm in chat, then run (no TTY in Claude's shell):
   ```bash
   ASSUME_YES=1 bash scripts/deploy/test/sync-from-prod.sh
   ```
   (Interactive use without ASSUME_YES asks you to type the target DB name.)

## What it does on the server

1. Guards: distinct DBs / roots / MySQL users, the test `.env` points at the test DB, the
   test MySQL user **cannot** read the prod DB, the test venv exists.
2. Dumps prod → `/opt/school-management-test/backups/db_prodclone_<ts>.sql.gz` and checks
   it ends with `Dump completed` (the test DB is untouched until then).
3. Backs up the current test DB → `db_presync_<ts>.sql.gz`.
4. Stops `school-management-test`, DROP + CREATE `school_management_test`, imports,
   verifies the alembic revision equals prod's and prints prod/test row counts.
5. `alembic upgrade head` with the code deployed on TEST (a real migration rehearsal when
   TEST runs newer code than prod).
6. Starts the service; health check from the Mac.

## After running

- Show: the prod revision, the row-count table, the final test revision, the dump path and the health result.
- Logins on TEST are prod's real credentials (hashes are cloned). Email is disabled on TEST.

## Recovery

If it failed after the drop, the script prints the exact command to restore `db_presync_<ts>.sql.gz`.
