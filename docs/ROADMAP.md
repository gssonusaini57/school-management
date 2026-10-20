# KIS School Portal — future work (not scheduled)

Ideas for the next year, collected on 2026-10-19 and updated on 2026-10-20 after the prod
go-live. Nothing here is committed to or started; the list exists so decisions can be made with
the whole picture in view. Sizes are rough: S = days, M = a week or two, L = several weeks.
"Depends on" names what must exist first.

**Live on https://kisschool.in since 2026-10-20:** Results v2 (term/annual results, rank,
attendance, letter grades, report cards with background PDFs and ZIP), optional subjects
(11th/12th Mathematics), admin and teacher dashboards, the side-menu app with brand colours and a
theme option, and "stay signed in" (website Remember me, fingerprint/face sign-in and saved
accounts in Android app 1.3.4).

## Waiting on the school (not development work)

| Item | Who | Why it matters |
|---|---|---|
| Tick the real Mathematics takers in 11th and 12th (Class Subjects → Mathematics) | super-admin | Until then nobody can enter Mathematics marks in those classes |
| Approve renaming mistyped exam names in 11th/12th English ("PT First" → "P.T. First", "P.T Second" → "P.T. Second") | principal | Otherwise a per-exam report card prints them as separate columns |
| Spot-check the seeded exam pattern for 9th–10th against the handwritten sheet | super-admin | Some maximum marks were ambiguous when the pattern was entered |
| Attendance adoption: only 6 of 15 classes marked any attendance in October 2026; 4 marks tests are still drafts | principal | Dashboards and report cards can only be as complete as the data |
| Should staff holding the Fees menu also record and delete payments? (today: they can view, only admins record) | owner | Decides the next Fees change |

## Do these first

| # | Feature | Why first |
|---|---|---|
| 1 | **Nightly off-box database backups** (`mysqldump` + uploaded files to object storage, 30-day retention, a tested restore) | Backups today are manual (`backup-db.sh` to one laptop). Small job, removes the one risk that can erase everything. |
| 2 | **Fee structure + dues ledger** (fee heads, monthly dues, concessions, defaulter list) | Today the system only records payments, and none have been recorded on prod yet. Every finance feature below depends on knowing what is owed. |
| 3 | **WhatsApp / SMS notice broadcast** (per class, templates, delivery log) | The most visible value for parents; also unlocks absent-today alerts and "attendance not marked" reminders. Needs a provider account and DLT registration. |
| 4 | **Offline-first attendance in the app** (local queue, sync, server wins) | Classrooms with weak signal. The dashboards now show which classes didn't mark attendance, so make marking it easy. |
| 5 | **Session-end promotion workflow** (bulk promote / detain from results, roll-number reset, archive the year) | Hard deadline: the first time the system must roll from 2026-27 to 2027-28 (March 2027). |

## Academics

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Session-end promotion workflow (see above) | admin | L | sessions + results (live) |
| Timetable with substitutions for an absent teacher | admin, teachers | M | staff leave |
| Homework / diary per class and subject, with a photo | teachers, parents | M | parent app or WhatsApp |
| Exam date-sheet, seating plan and invigilation duty PDFs | admin | M | PDF pipeline (exists) |
| Exam-name guard: refuse new component names that differ from the standard ones only by dots/spaces | admin, report cards | S | the principal's rename decision |
| More optional/elective subjects (e.g. 11th/12th stream electives) using the optional-subject ticks | admin | S | optional subjects (live) |

## Attendance

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Offline-first attendance (see above) | teachers | M | Android only |
| "Attendance not marked yet" reminder to class teachers (~10:00) | principal, teachers | S | push notifications or WhatsApp |
| Absent-today parent alert (SMS / WhatsApp around 10:30) | parents | S+ | messaging provider + DLT |
| Monthly attendance register PDF with 75 % eligibility warnings | admin, PSEB | S | PDF pipeline |
| Staff attendance and leave (CL / EL / ML balances) feeding salary slips | staff, admin | M | salary slips (exist) |

## Fees and finance

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Fee structure + dues ledger (see above) | admin, finance | L | replaces the payments-only model |
| Let Fees-menu staff (the accounts clerk) record payments, with an audit trail | admin, clerk | S | the owner's decision above |
| Defaulter reminders and a UPI / payment-gateway link | parents, admin | M | ledger + gateway account |
| Daily collection register, cash / bank reconciliation | admin | S | ledger |
| Transport routes and stops with a bus-fee head | admin, parents | M | ledger |

## Communication and parents

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| WhatsApp / SMS notice broadcast (see above) | parents | M | WhatsApp Business API provider (e.g. Gupshup, MSG91) |
| Parent Android app: attendance, report card, notices, fee receipts; OTP login | parents | L | OTP SMS, parent-scoped API |
| Parent–teacher meeting scheduling and feedback | parents, teachers | S | parent app or WhatsApp |

## Staff and HR

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Staff profiles, documents, PSEB staff statement, staff ID cards | admin | M | PDF pipeline |
| Staff leave and attendance (see Attendance) | staff, admin | M | — |

## Admin, security and compliance (PSEB)

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Transfer / school-leaving, bonafide and character certificates with a serial register | admin, parents | S | letterhead templates (exist) |
| Student ID cards (class-wise PDF sheet, photo + QR) | admin | S | student photos (exist) |
| Audit log: who changed what and when, super-admin view | super-admin | M | — |
| Nightly off-box backups (see above) | everyone | S | — |
| PSEB export sheets (registration, CCE marks, roll statements) as Excel | admin | M | results engine |
| Website "Signed-in devices" page and an admin "sign out a lost phone" button (the server already supports both; today only the app shows the devices list) | everyone, admin | S | stay signed in (live) |
| Rate-limit sign-in and session renewal in nginx (`limit_req` on `/api/auth/login` and `/api/auth/refresh`); the app already blocks 10 wrong passwords in 15 minutes | everyone | S | — |
| Shorten the 1-hour sign-in token to 15–30 minutes once every phone runs app 1.3.4 | everyone | S | app 1.3.4 adoption |
| Add `AUTH_COOKIE_PATH` to `deploy/.env.example` and the provisioning script (TEST needs `/kisschool/api/auth`) | ops | S | — |

## Reports and analytics

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Trends: monthly attendance, subject mark distributions, teacher entry status, CSV export | admin | M | the class-summary and marks-summary endpoints (live) |

## Platform and technology

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Punjabi UI completion: extract the Android app's strings (none are in resources today) and add `values-pa`; finish the older portal pages (Students, Attendance, Fees, Staff, Reports) | teachers | M | Noto Sans Gurmukhi |
| Push notifications for approvals, notices and reminders (Firebase Cloud Messaging or self-hosted ntfy) | teachers | S | a push service |
| iOS: ship the portal as an installable web app first; native app later (the iOS scaffold has none of the 2026 features) | iOS users | L | — |
| Uptime and error monitoring (Sentry, health-check pings); make `/check-logs` show only tracebacks inside the chosen time window | admin | S | — |
| Code-split the website (bundle ≈ 1.4 MB): lazy-load reports, templates and class-subjects pages | everyone | S | — |

## Small items deferred

- Marks Entry (web): the class, subject and test pickers have no labels for screen readers.
- Report cards tab (web): on a 1440 px laptop the table's last column is cut off and needs a sideways scroll.
- Android "Marks to finish" opens Marks Entry on the right class but doesn't pre-select the subject and test.
- Android History screen: a half day shows a grey dash (no "H" badge case).
- Android light theme: the spinner on a busy, disabled "Report card" button is barely visible.
- Android document photos upload at full camera size (the website compresses to ~900 px first).

## Done since this list was written

- 2026-10-20: prod Android release (1.3.4 build 25) — was due before 1 January 2027.
- 2026-10-20: Fees page works again for staff holding the Fees menu.
