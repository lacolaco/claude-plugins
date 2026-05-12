#!/bin/bash
# Stop / StopFailure hook adapter.
#
# Uses Claude Code's `decision: "block"` mechanism to make Claude run
# ONE more action — a mid-turn say with a short Japanese summary —
# *inside the same turn* before the turn truly stops. The hook fires
# again after Claude's follow-up action, and the second firing sees
# `stop_hook_active=true` and exits cleanly (no infinite loop).
#
# Why not just stream `last_assistant_message`: full-text playback ran
# tens of seconds on multi-paragraph responses, way too long. Letting
# Claude author its own one-line summary, then speaking THAT, gives
# the instant audio feedback the user wants without dragging.
#
# No-op when the session has no voice assigned or has been silenced via
# /session-tts:tts off.

set -e

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
stop_hook_active=$(printf '%s' "$input" | jq -r '.stop_hook_active // false')

data_dir="$HOME/.claude/session-tts"
[ -z "$session_id" ] && exit 0
[ ! -e "$data_dir/sessions/$session_id" ] && exit 0
[ -e "$data_dir/silenced/$session_id" ] && exit 0

# Second firing of the Stop hook within the same logical turn (because
# we blocked the first one and Claude did its follow-up). Now let the
# turn truly end — no audio nag, no infinite loop.
if [ "$stop_hook_active" = "true" ]; then
  exit 0
fi

plugin_root="${CLAUDE_PLUGIN_ROOT}"
# Stop hook schema only supports: decision, reason, continue,
# suppressOutput, stopReason, systemMessage. hookSpecificOutput /
# additionalContext are PreToolUse / PostToolUse / UserPromptSubmit /
# PostToolBatch only — Stop must put its instruction text in `reason`.
jq -n --arg cmd "bash \"$plugin_root/skills/say/say.sh\" \"<phrase>\"" '{
  decision: "block",
  reason: ("[session-tts] Before this turn truly ends, summarize what you just did in ONE short Japanese phrase (≤100 chars, open with a lead-in like 「報告です。」/「完了です。」/「方針転換です。」) and speak it RIGHT NOW by calling: `" + $cmd + "`. run_in_background=true is REQUIRED. After that one Bash call, produce a brief acknowledgement text and stop — do not start new work. (The Stop hook will fire again with stop_hook_active=true and let the turn end cleanly.) Skip the say call only if you already invoked say.sh in the immediately preceding step with the same conclusion; in that case just stop.")
}'
