#!/bin/bash
# Stop / StopFailure hook adapter.
#
# Reads the hook payload, takes `last_assistant_message`, and speaks it
# through the shared voice context. No `decision: block`, no loop, no
# next-turn deferral — just the same direct playback path the Stop hook
# has used since v0.7.3.

set -e

# shellcheck source=lib/voice-context.sh
. "${CLAUDE_PLUGIN_ROOT}/scripts/lib/voice-context.sh"

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
text=$(printf '%s' "$input" | jq -r '.last_assistant_message // empty')

[ -z "$text" ] && exit 0

speaker_id=$(resolve_speaker "$session_id") || exit 0
speak_text "$speaker_id" "$text" "$session_id"
