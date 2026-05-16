Analyze our entire conversation and current project state, then save comprehensive context to Claude Code-native locations.

## FILE 1: .claude/CLAUDE.md
(Project Memory — Claude reads this automatically on every session start)

**IMPORTANT SIZE MANAGEMENT:**
- CLAUDE.md must stay under 500 lines. If it exceeds 500 lines after your edits:
  - Archive old sessions (keep only last 3) to `.claude/SESSION_HISTORY_{range}.md` with a reference link
  - Archive old gotchas (keep only last 15) to `.claude/GOTCHAS_{range}.md` with a reference link
- Existing archives: check for `SESSION_HISTORY_*.md` and `GOTCHAS_*.md` — append to these or create new ones
- Use `Edit` tool for incremental updates, not full file rewrites

### Required Sections:

**# Project Memory** — Last Updated + session count + links to commands/ and skills/

**## Project Overview** — What this project is, its purpose, and goals.

**## Tech Stack** — Languages, frameworks, libraries, and tools with versions.

**## Architecture** — Key components, folder structure, ASCII diagrams. Keep concise.

**## Session History** — PREPEND new session at top. Keep only last 3 sessions inline. Archive older ones to `SESSION_HISTORY_*.md` files with a reference link like:
> Sessions 1–6 archived → See [SESSION_HISTORY_1_6.md](./SESSION_HISTORY_1_6.md)

**## Current Status** — Working ✅, Broken ❌, In Progress 🔄

**## Next Steps / TODOs** — Pending tasks in priority order.

**## Key Files** — Table of important files and their purpose.

**## Important Commands** — How to run, build, test, and deploy.

**## Environment & Config** — Servers, ports, DB, profiles, paths.

**## Flyway Migration History** — Table of all migrations (skip section if not a Java/Flyway project).

**## Gotchas & Notes** — Keep only last 15 items inline. Archive older ones to `GOTCHAS_*.md` with reference link like:
> Items 1–24 archived → See [GOTCHAS_1_24.md](./GOTCHAS_1_24.md)

**## Post-Cyber-Attack Changes** — Keep the existing table if present.

**## Documentation** — Pointers to docs/ folder.

Add at bottom:
> Context usage guide: 0–60% work freely | 60–70% monitor usage | 70–80% run /compact | 80%+ run /clear (mandatory)

## FILE 2: .claude/skills/<skill-name>/SKILL.md
(Only for skills created, modified, or discussed this session)

## FILE 3: .claude/commands/<command-name>.md
(Only for commands created, modified, or discussed this session)

## GLOBAL RULES
1. Never overwrite session history — always prepend new sessions.
2. Keep Gotchas cumulative — archive old ones to sub-files, never delete.
3. Write with enough detail that a fresh Claude Code session can continue with zero questions.
4. Use `Edit` tool for CLAUDE.md updates — never full rewrite.
5. Target: CLAUDE.md under 500 lines. Archive aggressively.
6. Also update the persistent memory files at the memory/ directory (user, feedback, project, reference types).
