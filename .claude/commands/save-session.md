# Command: /save-session
<!-- prompt-library-version: 2026-08-31 -->

## Description
Save full session context to `.claude/CLAUDE.md` plus per-workstream archives,
keeping sessions, gotchas, skills, and commands deduplicated and in sync.

## When to Use
At the end of a working session, or before `/compact` or `/clear`, so the next
session can resume with zero questions.

## Project-Specific Notes
<!-- Local customizations go BELOW this line. They are preserved across updates. -->

**P1 — ARCHIVE LAYOUT (this project overrides the generic model).** This project
archives **flat in `.claude/`, numbered by session**, not under
`.claude/sessionhistory/` by task-slug:
- Sessions → `.claude/SESSION_HISTORY_<n>.md` or `_<n>_<m>.md`
  (existing: `1_2`, `3`, `4`, `5`, `6`, `7`, `8_9`, `12`).
- Gotchas → `.claude/GOTCHAS_<a>_<b>.md`
  (existing: `1_6`, `7_12`, `13_21`, `INLINE_1_4`).
- There is no `GOTCHA_INDEX.md`; the `## Conventions / Gotchas` section of
  CLAUDE.md holds the **full inline gotcha bodies** (last ~19), with `>` pointer
  lines to the archived ranges at the top.
- Gotcha numbers **restart from 1 after an archive sweep** (so the live inline
  list is 1..N and all `(Gotcha #n)` cross-references in CLAUDE.md point at that
  live list, not at a global monotonic sequence). Keep it that way — renumbering
  would break every cross-reference in the session history.
- Some sessions are recorded in **memory files only** (no `SESSION_HISTORY_*.md`),
  referenced from the pointer list as `— see memory \`<slug>\``. That is fine;
  do not manufacture an archive file just to fill the gap.

**P2 — MEMORY IS ONE DIRECTORY, REACHED BY TWO PATHS (symlink).** Claude Code's
auto-loaded memory path for this project is a **symlink into the repo**:
`~/.claude/projects/-Users-manjeetsaini-Documents-GitHub-school-management/memory`
-> `<repo>/.claude/memory`. So there is a single set of files, they cannot drift,
and writing through either path is sufficient — do **not** double-write or diff
them. Memory edits therefore show up in `git status` and get committed with the
repo. Verify the symlink still holds with
`python3 -c "import os;print(os.path.realpath(os.path.expanduser('~/.claude/projects/-Users-manjeetsaini-Documents-GitHub-school-management/memory')))"`
and only fall back to syncing two real directories if that ever stops resolving
into the repo.

**P3 — Required CLAUDE.md sections this project keeps** (in addition to the
generic list below). Preserve them verbatim if present; do not drop them:
- `## Flyway Migration History` — Table of all migrations (skip section if not a
  Java/Flyway project). *This project uses **Alembic**, not Flyway: the
  equivalent lives inline in `## Database Schema` + the `backend/alembic/versions/`
  note. Do not add an empty Flyway section here.*
- `## Post-Cyber-Attack Changes` — Keep the existing table if present.
- `## Important Commands` — how to run, build, test, deploy.
- `## Environment & Config` — servers, ports, DB, profiles, paths.
- `## Documentation` — pointers to the docs folder.
- `## Live URLs`, `## API Endpoints`, `## Repo Layout`, `## Database Schema`,
  `## Frontend Routes`, `## Slash Commands`, `## Server-side Layout` — this
  project's own long-standing sections. Update in place; never delete.

**P4 — Commit messages carry NO attribution trailer.** Never append
`Co-Authored-By: Claude ...` or `Generated with Claude Code` to commits or PR
descriptions in this project. See memory `feedback_no_claude_coauthor`.

**P5 — Frontend typecheck command.** When verifying frontend edits before
recording them, use `npx tsc -b` (what `npm run build` runs). `npx tsc -b --noEmit`
fails on this repo's project-references config with TS6310.

**P6 — No secrets, but DO record login identifiers.** This project's CLAUDE.md
intentionally records admin/super-admin **email identifiers** and the seeded
default password hint (`admin123`) because they are shared test credentials.
Never record the real super-admin password, SMTP password, keystore password, or
DB password — only their variable names / file locations.

## Instructions

Analyze the entire conversation and current project state, then save comprehensive context. Create any folders that don't already exist (`.claude/`, `.claude/commands/`, `.claude/skills/`, `.claude/doc/`).

Read existing files FIRST before writing: `.claude/CLAUDE.md`, the `.claude/SESSION_HISTORY_*.md` + `.claude/GOTCHAS_*.md` archives, `.claude/commands/`, `.claude/skills/`, `.claude/doc/`, and BOTH memory directories (see P2).

**ARCHIVE MODEL (as overridden by P1 above — read that first):**
- History is archived **by session number, flat in `.claude/`** — `SESSION_HISTORY_<n>.md` for narrative, `GOTCHAS_<a>_<b>.md` for swept gotcha ranges.
- CLAUDE.md stays the always-loaded rolling summary: the last ~3 distinct workstreams inline under `## Session History`, and the full live gotcha list under `## Conventions / Gotchas` with `>` pointers to the archived ranges.

**IMPORTANT SIZE MANAGEMENT:**
- CLAUDE.md must stay under 500 lines. If it exceeds 500 lines after your edits:
  - Move the oldest inline session narrative out into its `SESSION_HISTORY_<n>.md` and leave a one-line `>` pointer (keep only the last 3 DISTINCT workstreams inline).
  - Sweep the oldest inline gotchas into a new `GOTCHAS_<a>_<b>.md`, add a `>` pointer line, and restart the live inline numbering at 1 — then fix every `(Gotcha #n)` cross-reference in the file to match the new live numbers.
- Existing archives: enumerate `.claude/SESSION_HISTORY_*.md` + `.claude/GOTCHAS_*.md` — append into the matching file, do not spawn near-duplicates.
- Use targeted edits for incremental updates, not full-file rewrites.

---

## PHASE 0 — SCAN ALL HISTORY FIRST (SESSIONS + GOTCHAS + ROLLING SECTIONS), THEN MERGE

Run this FIRST — before writing ANY new session block, gotcha, or Current Status / Next Steps / Key Files line. The rule is **club, don't duplicate, across the FULL corpus (inline AND archived)**, not just what is inline. Scan ONCE, hold the indexes in memory, then do every merge in ONE pass.

**S1 — Build the Workstream Index (inline + archived).**
- List `.claude/SESSION_HISTORY_*.md` and read each — note the sessions it covers, the workstreams/topics/ticket-IDs in it, and its file-set. Also read the inline `## Session History` in CLAUDE.md, including every `> Session <n> (...) → [SESSION_HISTORY_<n>.md]` pointer line and every `— see memory \`<slug>\`` pointer.
- One row per workstream: `{session number(s), topic-or-feature, file-set, location = inline | archive:<file> | memory:<slug>, current-state one-liner}`. Workstream key = same topic / feature / incident / ticket ID / file set that STEP 0 uses.

**S2 — Build the Gotcha Index (inline + archived).**
- Read the `## Conventions / Gotchas` section of CLAUDE.md (the live numbered list) and every `.claude/GOTCHAS_*.md`.
- One row per gotcha-fact: `{#n, subject one-liner, location, refines/extends chain}`. This is what lets a new gotcha be recognised as a duplicate/refinement of an existing one — and merged into it — instead of minting a redundant number.
- While here, verify every `(Gotcha #n)` cross-reference elsewhere in CLAUDE.md still points at the right live item. Archive sweeps renumber the live list, so these go stale silently. Fix any that drifted.

**S3 — Route SESSIONS using the Workstream Index:**
- Same workstream as an INLINE entry -> **CLUB** into it (STEP 0 below).
- Same workstream that lives only in an ARCHIVE file or a MEMORY file -> **append the new still-true facts there** (edit in place) and refresh the inline `>` pointer line (date / one-line summary). Pull a workstream back inline only if it is now the active focus again; if so, also trim the archived copy so there are not two live copies.
- Genuinely new workstream -> write a fresh inline block (and an archive file only when it is later evicted from inline by the size rule).
- AFTER, re-apply the size rule: keep only the last 3 DISTINCT workstreams' narrative inline; move the oldest distinct one's body into its `SESSION_HISTORY_<n>.md`, leaving a pointer.

**S4 — Route GOTCHAS using the Gotcha Index:**
- Duplicates / refines / corrects an EXISTING gotcha -> merge the new fact into that `#n` in place, keep the lower (original) number, note the refinement. Mint NO new number for the same fact.
- Genuinely new -> next number = (max of the LIVE inline list) + 1; write the full body into `## Conventions / Gotchas`. Per P1, numbering is the live-list sequence, which restarts after an archive sweep — not a globally monotonic one.
- Cross-cutting / foundational gotchas still go in the same inline list; this project does not split gotchas per workstream.

**S5 — Apply the same scan-and-dedup to Current Status, Next Steps / TODOs, and Key Files.** Using both indexes, collapse repeated/stale lines about the same item (ticket ID / file / incident) into a single current line, and DELETE lines this session resolved or superseded — checking the archive + memory bodies too, not just the inline ones. Actively re-verify each TODO against the repo (does the migration exist now? is the commit pushed?) rather than trusting the previous session's wording.

**S6 — ONE consolidated pass.** Do not re-scan. With the indexes in hand, perform the session merge/append, the gotcha merge/append, the rolling-section dedup, the cross-reference fixes, and the `Last Updated` + session-count header refresh in a single update. Never both inline-add and archive-append the same fact; never double-append.

---

## FILE 1: .claude/CLAUDE.md

Single source of truth for all future sessions. If it exists, UPDATE it — never overwrite session history.

Write/maintain these sections in clean markdown:

```
# Project Memory

> **Last Updated:** <date> | **Sessions:** <n> (<range> archived) | **Branch:** <branch> | **Stage:** <one-line>

> Slash commands: see [.claude/commands/](./commands/)

## Project Overview
What this project is, its purpose, and its goals.

## Tech Stack
Languages, frameworks, libraries, and tools with versions.

## Architecture / Repo Layout
Key components, services, folder structure, and how they connect.
Use ASCII diagrams where helpful.

## Important Commands
How to compile, test, package, run, and deploy — exact commands with examples.

## Session History
### Session <n> — <date> · <short title>

**Branch**: `<current git branch name>`

What was discussed, decided, and built this session — key files
created/modified, problems solved, approaches chosen and why.
Always include which branch the work was done on.

**STEP 0 — CONSOLIDATE / CLUB SAME-WORKSTREAM SESSIONS (do this BEFORE prepending):**
Same work spread across several sessions must end up as ONE entry, not N near-duplicate blocks. Before adding anything, consult the **PHASE 0 Workstream Index (inline + archives + memory)** — an earlier same-workstream entry may already live in a `SESSION_HISTORY_<n>.md` or a memory file.
- **Detect duplicates**: does this session continue, repeat, or finish the SAME workstream as one or more earlier entries (inline OR archived OR memory-only)? Same workstream = same topic / feature / incident / ticket ID / file set.
- **If it matches an ARCHIVED or MEMORY-ONLY entry -> append to that file** (PHASE 0 S3) and refresh the inline `>` pointer. Pull it back inline only if it is the active focus again (then trim the archived copy so there are not two live copies).
- **If yes (inline) -> MERGE, do not prepend a new block:**
  1. Pick the most recent same-workstream entry as the **anchor**. Update its header to the **current date** (and bump the session number/range, e.g. `Session 7` + `Session 8` -> `Sessions 7-8`).
  2. Fold the still-true facts from the older same-workstream block(s) into the anchor — keep what is current, drop what was superseded, deduplicate overlapping lines.
  3. **DELETE the older now-merged session block(s)** from CLAUDE.md. Their full historical detail lives in the archive file.
  4. Result: one consolidated, current-dated entry — never two blocks describing the same workstream.
- **If no** (genuinely different workstream from every existing entry) -> prepend a new inline block.
- Apply the same club-and-dedup logic to **Current Status**, **Next Steps / TODOs**, and **Key Files**.

PREPEND a new (non-merged) session at top. Keep only the last 3 DISTINCT workstreams inline. Move older ones' narrative into `SESSION_HISTORY_<n>.md` with a reference link like:
> Session 12 (top-bar nav) → [SESSION_HISTORY_12.md](./SESSION_HISTORY_12.md)

> Note: merging removes a *redundant copy of the same workstream*, never unique history. Distinct workstreams keep their own archive file.

## Current Status / Status table
- Working ✅
- Broken or buggy ❌
- In progress 🔄

## Next Steps / TODOs
Exact pending tasks in priority order, with enough detail that a
fresh session can pick them up without asking questions.
Delete every item this session actually finished.

## Key Files
| File | Purpose |
|------|---------|
| ... | ... |

## Environment & Config
Ports, environment variable names, external services, credential hints
(see P6 — identifiers yes, real secrets never). Runtime/SDK versions,
package-manager settings, deployment notes.

## Active MCP Servers
List servers configured in .mcp.json, what each one connects to,
and which skills or workflows depend on them.
(Write "None configured" if .mcp.json does not exist.)

## Active Hooks
List any hooks in .claude/settings.json (PreToolUse, PostToolUse,
SessionStart, SessionStop, PreCommit) and what each one does.
(Write "None configured" if no hooks exist.)

## Active Subagents
List any subagent definitions (e.g. .claude/agents/*.md), what each one is
responsible for, and which skills or commands they coordinate with.
(Write "None configured" if none exist.)

## Slash Commands / Custom Slash Commands
| Command | Purpose |
|---------|---------|
| /<name> | one line — what it does |

## Conventions / Gotchas
The LIVE numbered gotcha list, full bodies inline (this project keeps them in
CLAUDE.md — see P1). Lead with `>` pointer lines to the archived ranges:
> Items 1–6 archived → [GOTCHAS_1_6.md](./GOTCHAS_1_6.md)
Then `1.` … `N.` with the full text of each live gotcha.

## Documentation
Pointers to the docs folder / external references.
```

---

## FILE 2: .claude/SESSION_HISTORY_<n>.md — THE SESSION ARCHIVE

Shape:

```
# Session <n> — <date> · <short title>

**Focus:** <one line>

<narrative — preserve facts/tables/links verbatim when consolidating>
```

Rules:
- One session (or clubbed session range) per file; never two files describing the same workstream (CLUB them — same discipline as STEP 0).
- When a later session continues an archived workstream, append to that file and refresh the inline `>` pointer.

## FILE 2b: .claude/GOTCHAS_<a>_<b>.md — SWEPT GOTCHA RANGES

Created only by an archive sweep. Holds the full bodies of the gotchas removed from the live inline list, under their numbers **at the time of the sweep**. Add a `>` pointer line in CLAUDE.md. Never edit a swept gotcha's number.

---

## FILE 3: .claude/skills/<skill-name>/SKILL.md — DETECT, ADD, OR UPDATE A SKILL

Do not skip this section. Every save-session run must actively DECIDE whether the session produced a reusable capability worth capturing as a skill — and then add a new one or update/club an existing one. A skill is any repeatable, parameterizable workflow (a runbook, a multi-step analysis, a generator, a scan) — distinct from a one-off task.

**STEP A — Scan existing skills first.** List what already exists under `.claude/skills/` AND `.claude/commands/` (a capability may live as a command file, a `SKILL.md`, or both). Hold this inventory before deciding anything.

**STEP B — Decide per capability touched this session:**
- **No reusable capability** (pure investigation, one-off edits) -> do nothing here. Most sessions land here; that's fine.
- **New reusable capability that NO existing skill/command covers** -> ADD a new skill. Create `.claude/skills/<skill-name>/SKILL.md` (and/or a `.claude/commands/<name>.md` if it should be invokable as `/<name>` — see FILE 4). Register it: add a row to the Slash Commands table in CLAUDE.md.
- **Capability an existing skill ALREADY covers** (even partially / under a different name) -> UPDATE that skill in place. Do NOT create a second near-duplicate. Fold this session's new steps, flags, modes, gotchas, and false-positive patterns into the existing `SKILL.md` / command file.
- **Two skills now overlap** (this session blurred their scope, or a past session split one capability across two files) -> CLUB them: merge into the single best-named skill, redirect or delete the redundant one, and fix every reference (CLAUDE.md tables, links, other commands). Same club-and-dedup discipline as STEP 0 — one skill per capability, never two describing the same thing.

**STEP C — When ADDING or UPDATING, write the SKILL.md with this shape:**
```
---
name: <skill-name>
description: <one line — what it does + when to use it; this is what the picker shows>
---

# <Skill Name>

## When to Use
The trigger scenario(s).

## Inputs / Modes
Arguments, modes (e.g. quick|deep|full), and defaults.

## Steps
The exact numbered workflow to run.

## Gotchas / FP patterns
Anything learned this (or a prior) session that saves the next run time.

## Expected Output
What the skill produces or changes.
```

**STEP D — Keep command and skill in sync.** If a capability is both a skill and a `/command`, update BOTH files together this session, and make sure the CLAUDE.md command table reflects the current modes/description. A skill update that leaves the command table stale is incomplete.

---

## FILE 4: .claude/commands/<command-name>.md

Create or update command files for commands that were created, modified, or discussed THIS session. Apply the same **add / update / club** discipline as FILE 3: if a command for this capability already exists, UPDATE it in place rather than adding a near-duplicate; if two commands now overlap, merge them into one and fix all references. A command that is also a skill must be kept in sync with its `SKILL.md` (FILE 3, STEP D).

Structure for each:

```
# Command: /<command-name>

## Description
One sentence shown in the command picker.

## When to Use
The scenario this command is designed for.

## Steps
Numbered sequence executed when this command is invoked.

## Expected Output
What is produced or changed when the command completes.
```

---

## FILE 5: .claude/doc/ files

Only create or update documentation files that were generated or modified THIS session. Group them by subject in subfolders (e.g. `.claude/doc/architecture/`, `.claude/doc/monitoring/`, `.claude/doc/stories/`) and give each folder a `README.md` index once it holds more than a couple of files. Register the important ones in the CLAUDE.md `## Key Files` table.

---

## FILE 6: MEMORY FILES (see P2 — one directory, symlinked)

Update the persistent memory files in `.claude/memory/` (`user`, `feedback`, `project`, `reference` types) for anything durable this session established, and add/refresh its one-line row in `.claude/memory/MEMORY.md` (the index Claude loads each session). One write is enough — the user-level path is a symlink to this directory (P2).

Memory file shape:
```
---
name: <short-kebab-case-slug>
description: <one-line summary, used to decide relevance during recall>
metadata:
  type: user | feedback | project | reference
---

<the fact; for feedback/project, follow with the why and how-to-apply. Link related memories with [[their-name]].>
```
Check for an existing file that already covers the fact and UPDATE it rather than creating a duplicate. Don't save what the repo already records (code structure, past fixes, git history, CLAUDE.md).

---

## GLOBAL RULES

1. **Prepend distinct workstreams; CLUB continuations.** Add a brand-new inline session block ONLY for a genuinely different workstream. When this session continues/repeats/finishes the SAME workstream as an existing entry, MERGE — consolidate to the current date, deduplicate, and DELETE the older redundant block (see Session History -> STEP 0). **PHASE 0 runs first and scans the FULL corpus — the inline `## Session History` AND every `SESSION_HISTORY_*.md` AND the memory-only pointers; a continuation of a workstream that lives only in an archive or memory file is appended there (pointer refreshed), never re-told as a fresh inline block.** Never two blocks for one workstream; never silently lose surviving facts.
2. **Gotchas stay cumulative.** Add new items, never delete unless factually incorrect (then correct in place, keep the number). Detect duplicates/refinements against the PHASE 0 Gotcha Index (live inline list + `GOTCHAS_*.md`): a fact that duplicates/refines/corrects an existing gotcha is merged into that `#n` (lower number kept) — never re-minted. After any archive sweep, fix every `(Gotcha #n)` cross-reference in CLAUDE.md.
3. **Write with enough detail** that a brand-new session reading ONLY these files can continue work with zero questions.
4. **Use tables** for structured data: files, ports, scripts, env vars, host/service maps.
5. **Read before writing** — always read the existing CLAUDE.md, the relevant archive files, the memory files, and command files before updating, to avoid losing content.
6. **Use targeted edits** for CLAUDE.md + archive updates — never a full rewrite.
7. **Target: CLAUDE.md under 500 lines.** Archive aggressively. Clubbing same-workstream sessions, sweeping old gotchas, and deduping Current Status / Next Steps is how you stay under the limit.
8. **Always run the skill/command check (FILE 3 + FILE 4).** Every save-session run must decide whether this session produced a reusable capability and then ADD a new skill, UPDATE an existing one, or CLUB two overlapping ones — never leave a duplicate skill, and never leave the CLAUDE.md command table out of sync with the actual `.claude/commands/` + `.claude/skills/` files.
9. **PHASE 0 is mandatory and runs once, up front.** Before writing anything, scan ALL history for BOTH sessions and gotchas across BOTH inline and archived locations — plus the rolling sections (Current Status / Next Steps / Key Files) — build the two indexes, then combine/merge/update in ONE consolidated pass. No second re-scan, no double-append.
10. **No secrets** (see P6). Record credential *hints* (variable names, file locations, which vault/keystore) and shared test identifiers — never actual passwords, tokens, or keys.
11. **Update the memory files** (FILE 6). One directory, two paths — see P2; no double-write needed.
12. **No attribution trailer on commits** (P4).
13. **Add this context reminder** at the very bottom of CLAUDE.md:

> Context usage guide: 0–60% work freely | 60–70% monitor usage | 70–80% run /compact | 80%+ run /clear (mandatory)

---

## RESUME PROMPT (paste at the start of the NEXT session)

Read `.claude/CLAUDE.md` and continue from where we left off. If the work continues a workstream referenced by a `> Session <n> ... → SESSION_HISTORY_<n>.md` pointer (or a `— see memory <slug>` pointer), also read that file before starting.
