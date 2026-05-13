#!/bin/bash
# SessionEnd hook adapter. Fires when this session terminates
# (/clear, /compact, logout, etc.) and kills any in-flight TTS
# playback for this session so audio doesn't outlive the session
# that started it.
#
# Voice assignment (`sessions/<sid>`) and the silence flag
# (`silenced/<sid>`) are intentionally NOT touched: a /clear leaves
# the same session_id alive, and the next SessionStart re-fires on
# the same id — keeping those files makes the voice stable across
# clear/compact, which is the explicit goal in DESIGN §1.

set -e

input=$(cat)
session_id=$(printf '%s' "$input" | jq -r '.session_id // empty')

[ -z "$session_id" ] && exit 0

pidfile="$HOME/.claude/session-tts/playback/$session_id"
[ -f "$pidfile" ] || exit 0

pgid=$(cat "$pidfile" 2>/dev/null || echo "")
if [ -n "$pgid" ]; then
  # SIGTERM the recorded process group, bringing down the python
  # adapter and its afplay child together.
  kill -TERM -- "-$pgid" 2>/dev/null || true
fi
rm -f "$pidfile"

exit 0
