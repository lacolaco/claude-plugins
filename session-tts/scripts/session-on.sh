#!/bin/bash
# SessionStart hook handler.
#
# Two responsibilities:
#   1. Assign a voice to this session (rotating through the configured slots).
#      The assignment lives at $sessions_dir/$session_id; once written it is
#      kept across re-fires (clear/compact) so the voice stays stable for the
#      lifetime of the session.
#   2. Make sure the local TTS engine is installed, running, and has the
#      required voice models loaded. Idempotent — typical re-runs do nothing.

set -e

session_id=$(jq -r '.session_id // empty')
if [ -z "$session_id" ]; then
  exit 0
fi

data_dir="$HOME/.claude/session-tts"
sessions_dir="$data_dir/sessions"
index_file="$data_dir/index"
session_file="$sessions_dir/$session_id"

mkdir -p "$sessions_dir"

# --- pick a voice for this session (only if not already assigned) -----
if [ ! -f "$session_file" ]; then
  prev=$(cat "$index_file" 2>/dev/null || echo -1)
  case "$prev" in ''|*[!0-9-]*) prev=-1 ;; esac
  next=$(( (prev + 1) % 3 ))
  case "$next" in
    0) speaker_id=888753760  ;;  # voice slot 1
    1) speaker_id=1431611904 ;;  # voice slot 2
    2) speaker_id=345585728  ;;  # voice slot 3
    *) speaker_id=888753760  ;;
  esac
  echo "$next" > "$index_file"
  echo "$speaker_id" > "$session_file"
fi

# --- engine bootstrap (download/start/install voices) --------------------
# Run in the background so SessionStart returns instantly; the first hook
# that actually wants to speak will retry through the engine API.
nohup uv run --directory "${CLAUDE_PLUGIN_ROOT}/python" \
  python "${CLAUDE_PLUGIN_ROOT}/python/setup_engine.py" \
  >> "$data_dir/setup.log" 2>&1 < /dev/null &
disown
