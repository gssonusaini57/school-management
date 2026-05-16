# Gotchas — items 13–21 (archived 2026-05-08)

These were the inline gotchas 1–9 in the previous CLAUDE.md (deploy + provisioning era from Sessions 4–5). Stable now; rolled off the front page to keep CLAUDE.md under 500 lines.

13. **MySQL bucket name irrelevance.** The legacy Firebase Storage bucket name had a typo ("porfile"). Don't carry that forward. The MySQL DB is named `school_management` cleanly.

14. **`assert_class_allowed`** in [backend/app/deps.py](../backend/app/deps.py) is the server-side enforcement that replaces the old UI-only `.admin-only` class. Staff cannot read/write data for classes outside their `allowed_classes` even if they craft a URL.

15. **First-boot recipe on fresh server:** the systemd unit will fail-loop until `.env` exists with a valid `DATABASE_URL`. Provisioning step 04 always lands `.env` before step 05 enables systemd, but if you ever blow away `.env` while the service is running you'll get a CrashLoopBackOff.

16. **nginx `}server {` boundary.** The existing `expressonly.in` site config has `}server {` on a single line (no newline between blocks). Naive awk that "finds the last `}`" lands inside the wrong block. [scripts/provision/06-install-nginx-snippet.sh](../scripts/provision/06-install-nginx-snippet.sh) uses Python with brace-depth tracking + `listen 443` detection to insert into the SSL block specifically.

17. **nginx `alias` + nested regex location = footgun.** `location /school/ { alias …; location ~* \.js$ { alias …; ... } }` makes nginx prepend `/school/` to the inner alias → 404. Keep [deploy/nginx.school.conf](../deploy/nginx.school.conf) flat: outer `alias` already serves `/school/assets/foo.js` correctly. Vite's hashed filenames are cache-busting on their own; no inner caching block needed.

18. **`/opt/school-management/` must be 755, not 750.** nginx runs as `www-data`, which is not in the `school` group. Mode 750 → 500 errors trying to `try_files`. Step 02 sets 755 on the root dir; secret files inside (`.env`, `.my.cnf`, `.db_password`) stay 600 so privacy is preserved.

19. **`head -N | bash provision.sh` SIGPIPEs the SSH-driven `apt install`.** When `head` closes stdin after N lines, the pipe SIGPIPE propagates upstream and kills the local provisioning script (and the remote command via SSHD hangup). Don't pipe long-running deploys to `head`. Run the full script, then grep the saved log.

20. **MySQL root password on the test VPS** is `RootSecurePass2024Test`, set originally by `uploadmytds/scripts/server/mysql-install.sh`. Never hardcoded in this repo. Pass it as `MYSQL_ROOT_PASSWORD=… bash scripts/provision/provision.sh` (the script also prompts hidden if missing). For a future prod box, set whatever you want and pass it in the same way.

21. **Provisioning is idempotent — re-run is safe.** Every step has an `already-present?` short-circuit (apt: dpkg-query; user: `id school`; DB: `IF NOT EXISTS`; .env: file existence; systemd: `is-enabled`; nginx: `grep school.conf`). If something half-failed, just re-run `bash scripts/provision/provision.sh` — it picks up where it left off.
