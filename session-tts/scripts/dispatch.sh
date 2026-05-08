#!/bin/bash
# Hook dispatcher: forward stdin to say-response.py with the per-session
# speaker injected via env var. Skips silently if the session has no flag
# file (i.e. voice was turned off via /session-tts:tts off).
#
# Optional first argument: a fixed Japanese phrase. When set, the hook input's
# `last_assistant_message` is replaced with that phrase before forwarding.
# Used by Notification matchers (idle_prompt, permission_prompt) so that
# system payloads (which are English/freeform) are spoken as a known phrase.

set -e

fixed_message="${1:-}"

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
if [ -z "$session_id" ]; then
  exit 0
fi

data_dir="$HOME/.claude/session-tts"
session_file="$data_dir/sessions/$session_id"
silenced_file="$data_dir/silenced/$session_id"

# Session never assigned a voice (e.g. SessionStart hadn't fired) — skip.
if [ ! -e "$session_file" ]; then
  exit 0
fi
# User silenced this session via /session-tts:tts off — skip.
if [ -e "$silenced_file" ]; then
  exit 0
fi

speaker_id=$(cat "$session_file" 2>/dev/null || echo "")
if [ -z "$speaker_id" ]; then
  exit 0
fi

if [ -n "$fixed_message" ]; then
  payload=$(printf '%s' "$input" | jq --arg msg "$fixed_message" '. + {last_assistant_message: $msg}')
else
  payload="$input"
fi

printf '%s' "$payload" | SESSION_TTS_SPEAKER_ID="$speaker_id" \
  uv run --directory "${CLAUDE_PLUGIN_ROOT}/python" \
  python "${CLAUDE_PLUGIN_ROOT}/scripts/say-response.py"
