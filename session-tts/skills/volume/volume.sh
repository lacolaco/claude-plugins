#!/bin/bash
# /session-tts:volume skill entry point.
# Usage: volume.sh <0.0-1.0> | status | reset
#
# Persists the chosen value to ~/.claude/session-tts/volume so say-response.py
# can read it for every chunk. The setting is user-wide; concurrent sessions
# share it. An invalid value is rejected without touching the file so the
# previous setting (or the built-in default) stays in effect.

set -e

action="${1:-status}"
data_dir="$HOME/.claude/session-tts"
volume_file="$data_dir/volume"
default_volume="0.8"

show_status() {
  if [ -f "$volume_file" ]; then
    local current
    current=$(cat "$volume_file" 2>/dev/null || echo "")
    if [ -n "$current" ]; then
      echo "Claude TTS volume: $current (default: $default_volume)"
      return
    fi
  fi
  echo "Claude TTS volume: $default_volume (default)"
}

set_volume() {
  local value="$1"
  # Validate format first so awk's partial-number parsing (e.g. "0.5abc" → 0.5)
  # can't sneak through, then range-check with awk for proper float comparison.
  if ! [[ "$value" =~ ^[0-9]+(\.[0-9]+)?$ ]]; then
    echo "session-tts:volume: value must be a decimal in [0.0, 1.0]" >&2
    exit 1
  fi
  if ! awk -v v="$value" 'BEGIN { exit (v >= 0.0 && v <= 1.0) ? 0 : 1 }' </dev/null; then
    echo "session-tts:volume: value must be a decimal in [0.0, 1.0]" >&2
    exit 1
  fi
  mkdir -p "$data_dir"
  printf '%s\n' "$value" > "$volume_file"
  echo "Claude TTS volume: $value"
}

reset_volume() {
  rm -f "$volume_file"
  echo "Claude TTS volume: $default_volume (default)"
}

case "$action" in
  status)
    show_status
    ;;
  reset)
    reset_volume
    ;;
  *)
    set_volume "$action"
    ;;
esac
