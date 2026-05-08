#!/bin/bash
# Hook dispatcher: forward stdin to say-response.py only when the firing
# session's flag file exists. Scoping playback per session avoids cross-talk
# when multiple Claude Code sessions run concurrently.
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

flag="$HOME/.claude/kokoro-tts/sessions/$session_id"
if [ ! -e "$flag" ]; then
  exit 0
fi

if [ -n "$fixed_message" ]; then
  payload=$(printf '%s' "$input" | jq --arg msg "$fixed_message" '. + {last_assistant_message: $msg}')
else
  payload="$input"
fi

printf '%s' "$payload" | uv run --directory "${CLAUDE_PLUGIN_ROOT}/python" python "${CLAUDE_PLUGIN_ROOT}/scripts/say-response.py"
