#!/bin/bash
# Stop / StopFailure hook adapter.
#
# Reads the hook payload and speaks ONLY the end-of-turn summary —
# Claude's final paragraph in `last_assistant_message` — through the
# shared voice context. Mid-turn progress is already narrated by the
# LLM via /session-tts:say (nudged by TodoWrite / Monitor / Agent /
# UserPromptSubmit reminders), so reading the whole message at Stop
# would be redundant and long. The last paragraph is, per
# `~/.claude/CLAUDE.md`, "one or two sentences. What changed and
# what's next" — which is exactly the wrap-up the listener needs.

set -e

# shellcheck source=lib/voice-context.sh
. "${CLAUDE_PLUGIN_ROOT}/scripts/lib/voice-context.sh"

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')
text=$(printf '%s' "$input" | jq -r '.last_assistant_message // empty')

[ -z "$text" ] && exit 0

# Take the last non-empty paragraph (blank-line separated). Code fences,
# list blocks, and markdown the synthesizer can't render legibly are
# stripped downstream by say-response.py's `clean()`; here we only need
# the textual final block.
last_paragraph=$(printf '%s' "$text" | awk '
  BEGIN { RS = ""; last = "" }
  { last = $0 }
  END { print last }
')

[ -z "$last_paragraph" ] && exit 0

speaker_id=$(resolve_speaker "$session_id") || exit 0
speak_text "$speaker_id" "$last_paragraph" "$session_id"
