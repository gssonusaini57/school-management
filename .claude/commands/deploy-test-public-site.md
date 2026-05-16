---
name: deploy-test-public-site
description: Build the Eleventy public marketing site and deploy public-site/dist/ (static HTML) to the TEST server (104.237.5.113).
---

# Deploy public site → TEST

## Action

```bash
bash scripts/deploy/test/deploy-public-site.sh
```

## Pre-flight

- `git status` for `public-site/` — warn if dirty.
- Confirm `public-site/package.json` and `public-site/eleventy.config.cjs` exist.
- First-time deploys also need a manual nginx step — see `deploy/nginx.public-site.conf`.

## What the script does

1. SSH preflight.
2. Local: `cd public-site && npm ci && npm run build` (Tailwind CLI → `dist/css/site.css`, then Eleventy → `dist/{en,pa}/<slug>/index.html`).
3. Asserts `dist/index.html`, `dist/en/index.html`, and `dist/pa/index.html` all exist.
4. `rsync --delete public-site/dist/` → `/opt/school-management/public-site/dist/`.
5. `chown -R school:school /opt/school-management/public-site`.
6. Reminds the operator to apply the nginx snippet on first deploy.

## After first deploy — manual nginx step

The script does **not** modify nginx — that's a one-time manual step:

- For production (`khalsainternational.in`): use Pattern A in `deploy/nginx.public-site.conf` (separate `server { }` block + Let's Encrypt cert).
- For TEST preview on the existing host: use Pattern B (mounts the site under `expressonly.in/info/`). Add the snippet inside the existing expressonly.in server block, run `nginx -t`, then `systemctl reload nginx`.

## Live URLs after Pattern B is wired up

- https://expressonly.in/info/         → locale-detect redirect
- https://expressonly.in/info/en/      → English home
- https://expressonly.in/info/pa/      → Punjabi home
- https://expressonly.in/info/en/admissions/ → English admissions
- https://expressonly.in/school/       → React staff portal (unchanged)
