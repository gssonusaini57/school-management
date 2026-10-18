---
name: feedback-no-claude-coauthor
description: "Do NOT add the \"Co-Authored-By: Claude\" trailer to git commit messages on this project."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9abbe951-274e-4331-a756-26e1701ad176
---

Do not append `Co-Authored-By: Claude Opus ... <noreply@anthropic.com>` (or any Claude co-author trailer) to commit messages.

**Why:** User explicitly asked to remove it during the 2026-05-16 squash session — they don't want the signature on their commits.

**How to apply:** When creating commits (including squashes, amends, or HEREDOC'd messages) and PR descriptions, omit the Claude co-author trailer entirely — and the `Generated with [Claude Code]` line, and any other AI's attribution. This applies across all of this user's projects unless they say otherwise. Same holds for [[reference_uploadmytds_project]].

**This is now enforced, not just remembered** (asked for 2026-10-18, after a session instruction caused the trailer to be added anyway):
- `attribution: {commit:"", pr:"", sessionUrl:false}` in `~/.claude/settings.json` — kills Claude Code's **automatic** trailer globally. Note this does NOT stop the model from typing the trailer itself, which is exactly how it slipped through; a settings key cannot guard against that.
- `.githooks/no-ai-attribution.sh` + `.githooks/commit-msg` in school-management, armed by `git config core.hooksPath .githooks` (local config — **re-run it on every fresh clone**). Blocks the commit outright, whoever drives it.
- A `PreToolUse` Bash hook in that repo's `.claude/settings.json`, filtered to `git commit *` / `gh pr *`, fails fast before the command runs and is the only layer that sees a `gh pr create --body`.

**If the user asks for the same guardrail in another repo:** copy `.githooks/` + the `hooks` block of `.claude/settings.json`, then run the `core.hooksPath` command there. The rule itself lives in one file by design — edit `AI_NAMES` in `no-ai-attribution.sh` to cover a new model.
