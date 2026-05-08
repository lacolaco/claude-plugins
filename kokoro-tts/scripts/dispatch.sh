#!/bin/bash
# Hook dispatcher: forward stdin to say-response.py only when the firing
# session's flag file exists. Scoping playback per session avoids cross-talk
# when multiple Claude Code sessions run concurrently.

set -e

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')

if [ -z "$session_id" ]; then
  exit 0
fi

flag="$HOME/.claude/kokoro-tts/sessions/$session_id"
if [ ! -e "$flag" ]; then
  exit 0
fi

printf '%s' "$input" | uv run --directory "${CLAUDE_PLUGIN_ROOT}/python" python "${CLAUDE_PLUGIN_ROOT}/scripts/say-response.py"
