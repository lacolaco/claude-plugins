#!/bin/bash
# SessionStart hook handler: create the per-session flag so that the kokoro-tts
# Stop / StopFailure / Notification hooks speak by default in every new session.
# A user who wants a particular session silent can run `/kokoro-tts:voice off`
# at any time to delete the flag.

set -e

session_id=$(jq -r '.session_id // empty')

if [ -z "$session_id" ]; then
  exit 0
fi

dir="$HOME/.claude/kokoro-tts/sessions"
mkdir -p "$dir"
touch "$dir/$session_id"
