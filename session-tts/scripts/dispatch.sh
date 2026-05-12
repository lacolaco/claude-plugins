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

data_dir="$HOME/.claude/session-tts"
[ -z "$session_id" ] && exit 0
[ ! -e "$data_dir/sessions/$session_id" ] && exit 0
[ -e "$data_dir/silenced/$session_id" ] && exit 0

# Loop guard: file-based "did I just block?" flag. Per Claude Code docs,
# `stop_hook_active=true` is supposed to mark the second firing of the
# same Stop chain, but in practice (observed in interactive testing) it
# is not always passed through, leading to an infinite block loop. Trust
# only the flag we ourselves write here.
blocked_flag_dir="$data_dir/stop-blocked"
blocked_flag="$blocked_flag_dir/$session_id"
if [ -f "$blocked_flag" ]; then
  rm -f "$blocked_flag"
  exit 0
fi
mkdir -p "$blocked_flag_dir"
touch "$blocked_flag"

# Save the payload for debugging when something looks off — keep only
# the most recent one per session so disk usage stays bounded.
printf '%s' "$input" > "$data_dir/last-stop-payload.json" 2>/dev/null || true

plugin_root="${CLAUDE_PLUGIN_ROOT}"
# Stop hook schema only supports: decision, reason, continue,
# suppressOutput, stopReason, systemMessage. hookSpecificOutput /
# additionalContext are PreToolUse / PostToolUse / UserPromptSubmit /
# PostToolBatch only — Stop must put its instruction text in `reason`.
jq -n --arg cmd "bash \"$plugin_root/skills/say/say.sh\" \"<phrase>\"" '{
  decision: "block",
  reason: ("[session-tts] Before this turn ends, summarize what you just did in ONE short Japanese phrase (≤100 chars, open with a lead-in like 「報告です。」/「完了です。」/「方針転換です。」). Speak it by calling the **Bash tool** with these EXACT parameters:\n\n  command: " + $cmd + "\n  run_in_background: true\n  description: \"TTS turn summary\"\n\nThe `run_in_background: true` parameter (NOT a shell `&`) is REQUIRED so the turn does not block on synthesis. After that single Bash call, output a brief one-line acknowledgement and stop — do not start new work, do not investigate, do not call any other tool. (The Stop hook will fire again with stop_hook_active=true and let the turn end cleanly.) Skip the Bash call ONLY if you already invoked say.sh with the same conclusion earlier in this turn; in that case just stop.")
}'
