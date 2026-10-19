---
name: project_role_dashboards
description: Session 19 role dashboards + brand look — server class-summary and marks batches summary endpoints, web marked/pending classes pie + class-wise chart, Android drawer, admin vs teacher dashboards, module colours, light-default theme option. On TEST, not on prod.
metadata:
  type: project
---

**What the owner asked (2026-10-19):** admins/super-admins saw "No classes assigned" on Take attendance/Past attendance/Students (empty `allowed_classes` — fixed with `AuthRepository.visibleClasses`); replace the Home tile list with a ☰ menu and an attractive dashboard, different for admin and teacher; admin taps the Pending/Marked part of a classes pie → list of those classes → Back to the pie; colourful app with proper icons, light theme default with an option for dark/phone.

**What exists:** `GET /attendance/class-summary?from&to` (per class, ≤ 92 days, half day 0.5, scoped by `deps.classes_in_scope`) and `GET /marks/batches/summary?session[&class]`. Web Dashboard: admin "Class attendance today" pie + "Class-wise attendance" chart (Today/Week/Month, ≥ 90 / 75–89 / < 75 bands, 75 % PSEB line). Android (TEST app ≥ 1.3.2): drawer, admin dashboard (classes pie → `classes-today/{kind}` list screens, donut, class-wise bars, approvals or session, marks progress, fees, students & staff, notices), teacher dashboard (my classes today, class-wise, marks to finish, results readiness, session, notices), `KisModule` colour accents, Playfair Display Bold, `KisIcons`, Notices screen, theme Light/Dark/Same as phone.

**How to apply:** palette rules live in the `kis-design-system` skill; the owner approved the light look — don't redesign it. Insight to raise with the principal: only 6 of 15 classes marked attendance in October 2026. Related: [[project_android_dashboard_attendance]], [[project_results_aggregation]].
