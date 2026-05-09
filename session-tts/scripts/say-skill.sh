#!/bin/bash
# /session-tts:say skill entry point. Speaks a short Japanese phrase in
# the current session's voice.
#
# Usage: say-skill.sh "<short Japanese text>"
#
# session_id is taken from $CLAUDE_CODE_SESSION_ID (set by Claude Code for
# skill invocations). The skill receives no hook payload, so this adapter
# resolves the voice context independently from the hook adapters.

set -e

# shellcheck source=lib/voice-context.sh
. "${CLAUDE_PLUGIN_ROOT}/scripts/lib/voice-context.sh"

text="${1:-}"
session_id="${CLAUDE_CODE_SESSION_ID:-}"

[ -z "$text" ] && exit 0

speaker_id=$(resolve_speaker "$session_id") || exit 0
speak_text "$speaker_id" "$text"
