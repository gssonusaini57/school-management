# KIS School Portal — future work (not scheduled)

Ideas for the next year, collected on 2026-10-19. Nothing here is committed to or started;
the list exists so decisions can be made with the whole picture in view. Sizes are rough:
S = days, M = a week or two, L = several weeks. "Depends on" names what must exist first.

## Do these first

| # | Feature | Why first |
|---|---|---|
| 1 | **Nightly off-box database backups** (`mysqldump` + uploaded files to object storage, 30-day retention, a tested restore) | Nothing backs the data up off the server today. Small job, removes the one risk that can erase everything. |
| 2 | **Fee structure + dues ledger** (fee heads, monthly dues, concessions, defaulter list) | Today the system only records payments. Every finance feature below depends on knowing what is owed. |
| 3 | **WhatsApp / SMS notice broadcast** (per class, templates, delivery log) | The most visible value for parents; also unlocks absent-today alerts. Needs a provider account and DLT registration. |
| 4 | **Offline-first attendance in the app** (local queue, sync, server wins) | Classrooms with weak signal. The new dashboard will make missed attendance visible, so make it easy to mark. |
| 5 | **Session-end promotion workflow** (bulk promote / detain from results, roll-number reset, archive the year) | Has a hard deadline: the first time the system must roll from 2026-27 to 2027-28. |

## Academics

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Session-end promotion workflow (see above) | admin | L | sessions + results (exist) |
| Timetable with substitutions for an absent teacher | admin, teachers | M | staff leave |
| Homework / diary per class and subject, with a photo | teachers, parents | M | parent app or WhatsApp |
| Exam date-sheet, seating plan and invigilation duty PDFs | admin | M | PDF pipeline (exists) |
| Exam-name standardisation across classes (e.g. "PT First" → "P.T. First"), with a guard against new variants | admin, report cards | S | principal's approval of the mapping |

## Attendance

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Offline-first attendance (see above) | teachers | M | Android only |
| Absent-today parent alert (SMS / WhatsApp around 10:30) | parents | S+ | messaging provider + DLT |
| Monthly attendance register PDF with 75 % eligibility warnings | admin, PSEB | S | PDF pipeline |
| Staff attendance and leave (CL / EL / ML balances) feeding salary slips | staff, admin | M | salary slips (exist) |

## Fees and finance

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Fee structure + dues ledger (see above) | admin, finance | L | replaces the payments-only model |
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

## Admin and compliance (PSEB)

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Transfer / school-leaving, bonafide and character certificates with a serial register | admin, parents | S | letterhead templates (exist) |
| Student ID cards (class-wise PDF sheet, photo + QR) | admin | S | student photos (exist) |
| Audit log: who changed what and when, super-admin view | super-admin | M | — |
| Nightly off-box backups (see above) | everyone | S | — |
| PSEB export sheets (registration, CCE marks, roll statements) as Excel | admin | M | results engine |

## Reports and analytics

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Trends: monthly attendance, subject mark distributions, teacher entry status, CSV export | admin | M | the class-summary and batches-summary endpoints |

## Platform and technology

| Feature | Who benefits | Size | Depends on |
|---|---|---|---|
| Punjabi UI completion: extract the Android app's strings (none are in resources today) and add `values-pa`; finish the remaining portal pages | teachers | M | Noto Sans Gurmukhi |
| Push notifications for approvals and notices (Firebase Cloud Messaging or self-hosted ntfy) | teachers | S | a push service |
| iOS: ship the portal as an installable web app first; native app later | iOS users | L | — |
| Uptime and error monitoring (Sentry, health-check pings) | admin | S | — |
| Nightly off-box backups (see above) | everyone | S | — |

## Small items deferred on 2026-10-19

- Marks Entry (web): the class, subject and test pickers have no labels for screen readers.
- Report cards tab (web): on a 1440 px laptop the table's last column is cut off and needs a sideways scroll.
- Android History screen: a half day shows a grey dash (no "H" badge case).
- Android light theme: the spinner on a busy, disabled "Report card" button is barely visible.
- Prod Android app must ship before 1 January 2027: the current prod build (19) picks the wrong session name from January and the server will refuse its marks.
