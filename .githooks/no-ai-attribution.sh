#!/bin/sh
# Guardrail: reject AI / assistant attribution trailers in commit messages and
# PR bodies. Reads the text to check on stdin.
#
#   exit 0 -> clean
#   exit 1 -> a forbidden trailer was found (details on stderr)
#
# Used by two callers, so the rule lives in exactly one place:
#   .githooks/commit-msg                 -> every git commit, amend and rebase
#   .claude/settings.json PreToolUse     -> blocks the Bash call before it runs
#
# MODE (argv 1):
#   strict (default) - trailer must start a line. For a real commit message,
#                      where git trailers are always line-anchored.
#   loose            - also matches mid-line, for a one-line `git commit -m`.
#                      Fails closed: a commit message that merely *quotes* a
#                      trailer is rejected too. That is deliberate.
#
# To extend: add to AI_NAMES. Keep it lowercase; matching is case-insensitive.

MODE="${1:-strict}"

AI_NAMES='claude|anthropic|chatgpt|gpt-[0-9]|openai|copilot|gemini|codex|cursor|devin|windsurf|aider|llama|mistral|bard|assistant|\bai\b'

text=$(cat)

# An anchor that is either a line start (strict) or anything (loose).
case "$MODE" in
  loose) A='' ;;
  *)     A='^[[:space:]]*' ;;
esac

hit=''

# 1. Co-authored-by / Signed-off-by / Assisted-by naming an AI.
if printf '%s' "$text" | grep -qiE "${A}(co-authored-by|assisted-by|signed-off-by|committed-by)[[:space:]]*:[^$]*(${AI_NAMES})"; then
  hit='an AI co-author/assisted-by trailer'
fi

# 2. "Generated with Claude Code" and friends, with or without the robot emoji.
if printf '%s' "$text" | grep -qiE "${A}(.{0,4}[[:space:]]*)?(generated|created|written|authored)[[:space:]]+(with|by)[[:space:]]+\[?(${AI_NAMES})"; then
  hit='a "generated with <AI>" line'
fi

# 3. Known bot addresses and the session-link trailer.
if printf '%s' "$text" | grep -qiE '(noreply@anthropic\.com|users\.noreply\.github\.com>[[:space:]]*$.*copilot)'; then
  hit='an AI bot email address'
fi
if printf '%s' "$text" | grep -qiE "${A}claude-session[[:space:]]*:"; then
  hit='a Claude-Session trailer'
fi

[ -z "$hit" ] && exit 0

cat >&2 <<MSG
BLOCKED: commit/PR text contains ${hit}.

This project does not attribute commits or pull requests to Claude or any other
AI model. Remove the trailer and try again.

Rule: .githooks/no-ai-attribution.sh  (the one place to edit it)
Also:  ~/.claude/settings.json "attribution" suppresses the automatic trailer.
MSG
exit 1
