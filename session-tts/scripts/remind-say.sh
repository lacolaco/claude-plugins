#!/bin/bash
# Shared reminder hook adapter for session-tts.
#
# Usage: remind-say.sh <trigger>
#   <trigger> ∈ { todo | monitor | agent | prompt }
#
# Reads the hook payload from stdin (for the session_id) and, when the
# session has a voice and is not silenced, prints a trigger-specific
# reminder so Claude is nudged to narrate progress via the Bash tool +
# `${CLAUDE_PLUGIN_ROOT}/skills/say/say.sh` (synchronous; no
# run_in_background).
#
# Output format depends on the hook event:
#   - UserPromptSubmit (prompt): plain stdout — Claude Code auto-appends
#     it to the next turn's context.
#   - PreToolUse / PostToolUse (monitor/agent/todo): JSON with
#     `hookSpecificOutput.additionalContext`, since stdout is NOT
#     auto-injected for those events.

set -e

trigger="${1:-}"
[ -z "$trigger" ] && exit 0

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')

data_dir="$HOME/.claude/session-tts"
[ -z "$session_id" ] && exit 0
[ ! -e "$data_dir/sessions/$session_id" ] && exit 0
[ -e "$data_dir/silenced/$session_id" ] && exit 0

plugin_root="${CLAUDE_PLUGIN_ROOT}"
cmd="bash \"$plugin_root/skills/say/say.sh\" \"<phrase>\""

# Tail of every reminder — kept short and identical so the model
# pattern-matches it as boilerplate it can compress.
tail_common="Call Bash (synchronous; do NOT pass run_in_background) with command: \`$cmd\`. Open with a brief lead-in (報告です / 着手します / 完了です / 発見です / 方針転換です など), keep it under ~100 Japanese characters. The call blocks until playback finishes, so report only at real milestones. Skip if you just narrated in the immediately preceding step."

case "$trigger" in
  todo)
    event="PostToolUse"
    head="Todo state changed. Before your next text response, narrate this transition (前タスク完了 / 次タスク着手)."
    ;;
  monitor)
    event="PreToolUse"
    head="You are invoking Monitor — about to watch a long-running background task. Narrate WHAT you are monitoring and WHY."
    ;;
  agent)
    event="PreToolUse"
    head="You are invoking Agent — delegating a subtask to a sub-agent. Narrate WHAT you are delegating and the follow-up plan."
    ;;
  prompt)
    # UserPromptSubmit: stdout is auto-injected as context. No JSON.
    cat <<EOF
[session-tts] User prompt received. If this turn becomes multi-step,
narrate at milestones (transition / problem / finding / pivot).
$tail_common
EOF
    exit 0
    ;;
  *)
    exit 0
    ;;
esac

jq -n --arg event "$event" --arg msg "[session-tts] $head $tail_common" \
  '{ hookSpecificOutput: { hookEventName: $event, additionalContext: $msg } }'
