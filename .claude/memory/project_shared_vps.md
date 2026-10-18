---
name: Old TEST VPS shared with uploadmytds (historical)
description: HISTORICAL — until 2026-10 TEST lived on 104.237.5.113 alongside uploadmytds under expressonly.in/school/. Our SSH key is now rejected there; TEST moved to the prod box.
type: project
originSessionId: a28c76aa-d68b-4bf2-ac4b-fb655aa4a1d3
---
**Historical (superseded 2026-10-19 by [[project_test_instance_on_prod_box]]).**

Until Oct 2026 the TEST environment ran on **104.237.5.113** (Ubuntu 24.04), shared with uploadmytds (Tomcat :8080) and served at `https://expressonly.in/school/` via an include of `/etc/nginx/snippets/school.conf` inside the `expressonly.in` SSL block of `/etc/nginx/sites-enabled/test-angular`. SSH used `~/.ssh/uploadmytds_test`.

By 2026-10-18 that key was rejected (`Permission denied (publickey)`), so nothing could be deployed to or migrated off the box; TEST was rebuilt on 69.62.72.137 from a fresh prod clone. The box still belongs to uploadmytds — never touch its files (`/var/www/test-angular*/`, `/opt/pdffile/`, `/opt/tomcat/`, its nginx site) if access returns. The MySQL root password for that box lives in uploadmytds's own `scripts/server/mysql-install.sh`, not here.

**Why:** kept so references to "the old test box" / `expressonly.in/school` in history docs make sense.
**How to apply:** for anything current, use [[project_test_instance_on_prod_box]].
