---
name: deploy-prod-public-site
description: Build the Eleventy public marketing site and deploy public-site/dist/ to PROD (kisschool.in, served at the domain root). Requires "DEPLOY PROD" confirmation.
---

# Deploy public site → PROD

## Pre-conditions

- `scripts/deploy/prod/env.sh` is configured (it is — SERVER=69.62.72.137,
  DOMAIN=kisschool.in, SSH_KEY=~/.ssh/enamfoss_prod, SITE_BASE_PATH="").
- `git status` for `public-site/` — warn if dirty.

## Action

```bash
bash scripts/deploy/prod/deploy-public-site.sh
```

Type `DEPLOY PROD` when prompted.

## What the script does

1. `DEPLOY PROD` confirmation gate.
2. Local build with the prod base path: `SITE_BASE_PATH="" npm run build` (set by
   `prod/env.sh` via `common/lib.sh`) — so links/assets are root-relative (`/en/…`,
   `/css/…`, `/brand/…`), NOT `/school/…`.
3. Asserts `dist/index.html`, `dist/en/index.html`, `dist/pa/index.html` exist.
4. `rsync --delete public-site/dist/` → `/opt/school-management/public-site/dist/`.
5. `chown -R school:school`.

## nginx — already wired (no manual step on prod)

Unlike TEST, the prod vhost (`deploy/nginx.kisschool.conf` →
`/etc/nginx/conf.d/kisschool.conf`) already routes `location / { root …/public-site/dist; }`,
so the public site is live at the domain root after this deploy. No nginx edit needed.

## Live URLs after deploy

- https://kisschool.in/        → locale-detect redirect (→ /en/ or /pa/)
- https://kisschool.in/en/     → English home
- https://kisschool.in/pa/     → Punjabi home
- https://kisschool.in/admin/  → React staff portal (separate deploy)
- https://kisschool.in/api/    → FastAPI (separate deploy)
