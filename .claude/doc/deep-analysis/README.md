# KIS School Management — Deep-Analysis Knowledge Base

Durable onboarding reference for the **KIS School Management Portal** (Khalsa
International Senior Secondary School, Jalalabad). Written for an engineer who is
new to this repository and will maintain it for years: beginner-to-intermediate in
Python/FastAPI, React/TypeScript and Kotlin, but not new to programming.

| | |
|---|---|
| Generated | 2026-10-18 by the `/deep-analysis` command (prompt-library 2026-08-31) |
| Source state | branch `dev`, commit `8645bdd` (20 commits since the squashed root `307b7fc`, 2026-05-16) |
| Scope | everything tracked in the repo: `backend/`, `frontend/`, `public-site/`, `packages/`, `android/`, `ios/`, `deploy/`, `scripts/`, `.claude/`, `_handoff/`, `_archive/` |
| Companion | `.claude/CLAUDE.md` is the *operational snapshot* (what is deployed, what is next). This folder is the *durable explanation* (why things are shaped the way they are). When they disagree, the code wins and the disagreement is flagged here. |

## How to read this

Read in order over roughly a working week. Each document has one learning goal and
links forward and back. Paths are relative to the repository root. Anything the code
could not confirm is marked **UNKNOWN / needs owner confirmation** rather than guessed.
No credentials appear anywhere in these documents; where the repo itself contains
some, the file is named and the value is deliberately omitted.

| Day | Document | You will be able to… | ~Time |
|---|---|---|---|
| 1 | [00-project-overview.md](00-project-overview.md) | say what the system is, who uses it, where it runs, and what state it is in | 30 min |
| 1 | [01-domain-concepts.md](01-domain-concepts.md) | read a marks row, a report card or an attendance table and know what every field means | 45 min |
| 2 | [02-high-level-architecture.md](02-high-level-architecture.md) | draw the system on a whiteboard, including both deployment layouts, and explain why it is a monolith behind nginx | 45 min |
| 2 | [03-folder-structure-guide.md](03-folder-structure-guide.md) | find any file in under a minute and know which folders are safe to touch | 45 min |
| 3 | [04-core-modules-and-business-logic.md](04-core-modules-and-business-logic.md) | name the module that owns any rule, and the tables it reads and writes | 60 min |
| 3 | [05-execution-and-data-flow.md](05-execution-and-data-flow.md) | trace a request from nginx to MySQL and back, including the realtime fan-out, the PDF cache and the approval workflows | 60 min |
| 4 | [06-configuration-and-environment.md](06-configuration-and-environment.md) | configure a fresh server or a local dev box without guessing, and recognise the misconfigurations that have already bitten | 45 min |
| 4 | [07-design-patterns-and-tradeoffs.md](07-design-patterns-and-tradeoffs.md) | recognise the recurring patterns (approval queues, sentinel expansion, never-raises side effects, content-hash caches) and respect the parts that look old on purpose | 45 min |
| 5 | [08-risks-limitations-and-improvements.md](08-risks-limitations-and-improvements.md) | prioritise what to fix first, with evidence | 45 min |
| 5 | [09-onboarding-guide.md](09-onboarding-guide.md) | set up locally, make a safe first change, deploy it, and debug production | 60 min |
| ref | [10-glossary.md](10-glossary.md) | look up any term or acronym and jump to where it lives in code | as needed |

**If you only have one hour:** read 00, look at the diagram in 02, then do the
"first safe change" recipe in 09. Keep 10 open in a second tab.

## What is covered where (quick map)

```
                 ┌─────────────────────────────────────────────────────────────┐
  WHAT / WHY     │ 00 overview · 01 domain · 02 architecture · 07 trade-offs   │
                 ├─────────────────────────────────────────────────────────────┤
  WHERE          │ 03 folders · 04 modules · 10 glossary                       │
                 ├─────────────────────────────────────────────────────────────┤
  HOW IT RUNS    │ 05 flows · 06 configuration                                 │
                 ├─────────────────────────────────────────────────────────────┤
  WHAT TO DO     │ 08 risks & improvements · 09 onboarding                     │
                 └─────────────────────────────────────────────────────────────┘
```

## Keeping this current

* Re-run `/deep-analysis` after any session that adds a subsystem, a table, a
  deployment target or a client. The command merges rather than overwrites its own
  installation (see `.claude/commands/deep-analysis.md`).
* `/save-session` maintains `.claude/CLAUDE.md`; it does **not** maintain this folder.
  If a session changes something these docs assert (a route moved, a table renamed),
  edit the affected document in the same commit.
* The three hand-mirrored registries called out in 07 (class list, menu keys, grade
  bands) are the most likely things to drift silently. 08 lists the files.

## Other reference material in the repo

| Source | What it is good for |
|---|---|
| `.claude/CLAUDE.md` | live status, deploy commands, the numbered "Gotchas" list, session history |
| `.claude/GOTCHAS_*.md`, `.claude/SESSION_HISTORY_*.md` | archived rationale for older decisions (Firebase era, provisioning, nginx) |
| `.claude/memory/` | one-fact-per-file notes the AI assistant uses across sessions; good "why" source |
| `.claude/skills/kis-design-system/SKILL.md` | brand, token and bilingual rules that apply to any UI or print change |
| `scripts/README.md` | one-page deploy cheat-sheet |
| `android/README.md`, `ios/README.md` | mobile build and signing instructions (the iOS one is partly stale, see 08) |
| `STATUS.md` | a design-integration status report frozen on 2026-05-08; historical only |
| `README.md` (repo root) | **stale** — still describes the Firebase/GitHub Pages era; see 08 |
