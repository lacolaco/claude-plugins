#!/bin/bash
# /session-tts:tts skill entry point.
# Usage: tts.sh on|off|toggle|status
#
# When silencing the session (off / toggle-to-off), also kills any utterance
# that is still playing for this session. Without this, calling `tts off`
# while a long response is being read aloud would leave audio playing until
# the current chunk queue drains — surprising and frustrating.

set -e

action="${1:-status}"
session_id="${CLAUDE_CODE_SESSION_ID:-}"

if [ -z "$session_id" ]; then
  echo "session-tts:tts: CLAUDE_CODE_SESSION_ID is not set" >&2
  exit 1
fi

data_dir="$HOME/.claude/session-tts"
silenced_dir="$data_dir/silenced"
playback_dir="$data_dir/playback"
silenced_file="$silenced_dir/$session_id"

kill_current_playback() {
  # `off` should silence everything for this session — so walk every scope
  # subdirectory (main / say / ...) under playback/ and kill whichever
  # utterance is still in flight in any of them.
  for pidfile in "$playback_dir"/*/"$session_id"; do
    [ -f "$pidfile" ] || continue
    local pgid
    pgid=$(cat "$pidfile" 2>/dev/null || echo "")
    if [ -n "$pgid" ]; then
      # The pidfile holds the process-group leader's pid. SIGTERM to the
      # group brings down the python adapter and its afplay child together.
      kill -TERM -- "-$pgid" 2>/dev/null || true
    fi
    rm -f "$pidfile"
  done
}

silence_on() {
  mkdir -p "$silenced_dir"
  touch "$silenced_file"
  kill_current_playback
  echo "Claude TTS (this session): OFF"
}

silence_off() {
  rm -f "$silenced_file"
  echo "Claude TTS (this session): ON"
}

case "$action" in
  on)
    silence_off
    ;;
  off)
    silence_on
    ;;
  toggle)
    if [ -e "$silenced_file" ]; then
      silence_off
    else
      silence_on
    fi
    ;;
  status)
    if [ -e "$silenced_file" ]; then
      echo "Claude TTS (this session): OFF"
    else
      echo "Claude TTS (this session): ON"
    fi
    ;;
  *)
    echo "usage: tts.sh on|off|toggle|status" >&2
    exit 1
    ;;
esac
