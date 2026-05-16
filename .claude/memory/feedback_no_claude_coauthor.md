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

**How to apply:** When creating commits (including squashes, amends, or HEREDOC'd messages), omit the Claude co-author trailer entirely. This applies across all of this user's projects unless they say otherwise. Same likely holds for [[reference_uploadmytds_project]].
