#!/bin/bash
# /session-tts:say skill entry point. Speaks a short Japanese phrase in
# the current session's voice.
#
# Usage: say.sh "<short Japanese text>"
#
# session_id is taken from $CLAUDE_CODE_SESSION_ID (set by Claude Code for
# skill invocations). The skill receives no hook payload, so this adapter
# resolves the voice context independently from the hook adapters.

set -e

# Claude Code sets CLAUDE_PLUGIN_ROOT for hook invocations but NOT for the
# Bash tool, which is how this skill's adapter is reached. Resolve the
# plugin root from the script's own location (skills/say/ → ../..).
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
plugin_root="$(cd "$script_dir/../.." && pwd)"

# shellcheck source=../../scripts/lib/voice-context.sh
. "$plugin_root/scripts/lib/voice-context.sh"

text="${1:-}"
session_id="${CLAUDE_CODE_SESSION_ID:-}"

[ -z "$text" ] && exit 0

speaker_id=$(resolve_speaker "$session_id") || exit 0
speak_text "$speaker_id" "$text" "$session_id"
