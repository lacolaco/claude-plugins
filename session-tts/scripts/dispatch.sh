#!/bin/bash
# Stop / StopFailure hook adapter.
#
# Does NOT speak. Returns hookSpecificOutput.additionalContext so Claude
# Code injects a reminder into the model's context, nudging it to
# summarize the just-finished turn in one short Japanese phrase and
# announce it via the mid-turn say path at the START of the next turn.
#
# Why a reminder instead of direct full-text playback: reading the
# entire `last_assistant_message` aloud is too long — assistant
# responses run multiple paragraphs and the read-aloud takes tens of
# seconds. A model-authored summary is concise (≤100 chars) and serves
# as the audio sign-off for the turn that just ended.
#
# Trade-off: the audio fires when the NEXT turn starts (i.e. when the
# user submits the next message), not the moment the previous turn
# ended. The instant-feedback property of full-text Stop-hook playback
# is gone; in exchange the audio is short and the model decides what's
# worth saying.
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

plugin_root="${CLAUDE_PLUGIN_ROOT}"
jq -n --arg cmd "bash \"$plugin_root/skills/say/say.sh\" \"<phrase>\"" '{
  hookSpecificOutput: {
    hookEventName: "Stop",
    additionalContext: ("[session-tts] The previous turn just ended. Before responding to the new user prompt, summarize what you accomplished (or attempted) in that previous turn in ONE short Japanese phrase (≤100 chars, with a lead-in like 「報告です。」/「完了です。」/「方針転換です。」 etc.) and speak it via: `" + $cmd + "`. run_in_background=true is REQUIRED. After speaking, proceed to the user prompt normally. Skip if you already narrated the same conclusion in the previous turn via mid-turn say.")
  }
}'
