#!/bin/bash
# Stop / StopFailure hook adapter.
#
# Reads the hook payload from stdin, extracts `last_assistant_message`, and
# forwards it to the core (say-response.py) via the shared voice context
# helpers. The hook payload schema lives entirely inside this file — the
# core itself receives only plain text.

set -e

# shellcheck source=lib/voice-context.sh
. "${CLAUDE_PLUGIN_ROOT}/scripts/lib/voice-context.sh"

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
text=$(printf '%s' "$input" | jq -r '.last_assistant_message // empty')

[ -z "$text" ] && exit 0

speaker_id=$(resolve_speaker "$session_id") || exit 0
speak_text "$speaker_id" "$text" "$session_id"
