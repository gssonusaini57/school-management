---
name: uploadmytds project — sister project, deploy patterns to mirror
description: /Users/manjeetsaini/Documents/GitHub/uploadmytds is the user's other active project. Java/Spring Boot 3 + Angular 19 + MySQL 8 on Tomcat 11. Its scripts/deploy/ and .claude/commands/ are the canonical patterns school-management mirrors.
type: reference
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
Local path: `/Users/manjeetsaini/Documents/GitHub/uploadmytds/`

**Stack:** Spring Boot 3.4.5 (Java 21) + Angular 19 + Tomcat 11 + MySQL 8.0.45 + nginx 1.24. Flyway for migrations. JWT auth (Nimbus JOSE). HikariCP. Razorpay payments. Brevo + GoDaddy SMTP.

**Servers:**
- Prod: `104.237.2.140` (uses `~/.ssh/uploadmytds_prod`, root pwd `UpMyTDS@2026#Mx9k`)
- Test: `104.237.5.113` (uses `~/.ssh/uploadmytds_test`, root pwd `RootSecurePass2024Test`) — also runs school-management

**Deploy artifacts to mirror:**
- `.claude/commands/deploy-test.md`, `deploy-test-frontend.md`, `deploy-prod.md`, `deploy-prod-frontend.md`, `clean-logs.md`, `analyze-prod-logs.md`, `save-context.md`
- `scripts/deploy/test/deploy-test.sh`, `angular-frontend-test.sh`, `download-logs-test.sh`
- `scripts/deploy/prod/deploy-prod.sh`, `angular-frontend-prod.sh`, `download-logs-prod.sh`, `backup-prod-db.sh`, `deploy-nginx.sh`
- `scripts/server/mysql-install.sh` (provisioning template — credentials live in this file)

**Patterns:**
- 6× retry health check (10s interval)
- Backup-before-deploy + rollback on health-fail
- Date-based version bumping for cache eviction
- Color-coded shell output
- SSH wrapper functions, scp helpers
- Logs at `/opt/pdffile/logs/`, app at `/opt/tomcat/webapps/`
- Daily backup scheduler (10 PM, 30-day retention)
- Nightly mysqldump

**Note on coupling:** uploadmytds's deploy scripts have hard-coded local paths (`/Users/manjeetsaini/Documents/GitHub/uploadmytds/...`) — school-management's scripts use repo-root-relative paths so they're portable.

**How to apply:** When you need to add new ops tooling to school-management, look here first for an existing pattern. When you find one, port it idiomatically (don't copy verbatim — uploadmytds is Java/Tomcat/Maven and school-management is Python/gunicorn/pip).
