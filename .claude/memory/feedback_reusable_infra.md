---
name: Reusable infra preference — mirror uploadmytds patterns
description: When building deploy/provisioning tooling, mirror uploadmytds's slash-command + numbered-shell-script layout so test↔prod parity is automatic and one-off scripts are forbidden.
type: feedback
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
The user's exact ask after the migration scaffold was: "create skill + script that's reusable" — and pointed me at `uploadmytds/.claude/commands/` and `uploadmytds/scripts/deploy/` as the reference.

**The pattern they want every project to follow:**

1. **Slash commands** under `.claude/commands/<name>.md` — markdown specs that describe what to do, what to confirm, and what to verify. One per operation: `provision-test`, `deploy-test`, `deploy-test-frontend`, `deploy-test-all`, `deploy-prod*`, `clean-logs`.
2. **`scripts/deploy/{common,test,prod}/`** — common library, test scripts, prod scripts. Test and prod scripts are symmetric (just source different `env.sh`). Prod scripts require typing `DEPLOY PROD` to confirm.
3. **`scripts/provision/`** — numbered idempotent steps (01-…, 02-…, …) plus a `provision.sh` wrapper that runs them in order with a pre-flight read-only inspection and a `y` confirmation.
4. **No one-off scripts.** Every shell script must source a shared `env.sh` so server-specific values (IPs, keys, domains) are configurable. Promote test → prod by editing one env file, not by forking the scripts.
5. **Idempotent everywhere.** Re-running provisioning on a fully-provisioned server must complete without errors and without changing existing state. `IF NOT EXISTS` for SQL, `id <user>` checks for users, `grep || sed` for nginx config inserts, file-existence guards for `.env`.

**Why:** User runs both projects (uploadmytds, school-management) on the same VPS. Same hands operate them. Different deploy idioms = mistakes.

**How to apply:** When the user asks for new project infra, replicate this structure even if it feels heavyweight for a small project. The cognitive savings come later when test↔prod parity matters.
